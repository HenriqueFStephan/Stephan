#!/usr/bin/env python3
"""
Launch a Cursor cloud agent that gathers recent official and peer-reviewed sources on Brazil's NR-1 psychosocial risks and anonymous employee welfare questionnaires.

Coverage spans the updated NR-1, MTE guides, LGPD limits on worker questionnaires,
and related occupational-health literature. Only verifiable sources from the past
month that are not already in agents/data/discovered_sources.json survive the filter;
the surviving links are published as a GitHub issue titled
"[RESEARCH] NR-1 Welfare {date}".
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import textwrap
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_issue_solver_agents import (  # noqa: E402
    CURSOR_API_BASE,
    GITHUB_API_BASE,
    ApiError,
    _http_json,
    log,
)

DEFAULT_MODEL = "composer-2.5"
# Keep in sync with SKIP_LABELS in run_issue_solver_agents.py so a `solve` label
# never treats these digests as coding tasks. `[POST]` comments on
# law-research issues are a separate trigger.
DEFAULT_ISSUE_LABELS = ("law-research", "research")
DEFAULT_MIN_CONFIDENCE = 0.7
DEFAULT_MAX_PAPERS = 12
DEFAULT_POLL_INTERVAL_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 3600
DEFAULT_CLEANUP_OLDER_THAN_DAYS = 30
DEFAULT_MAX_AGE_DAYS = 31
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = REPO_ROOT / "agents" / "data" / "discovered_sources.json"
RESEARCH_CLEANUP_LABELS = frozenset({"research", "law-research"})
RESEARCH_CLEANUP_TITLE_MARKERS = ("[research]", "nr-1 welfare")

TERMINAL_STATUSES = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}

RESEARCH_TOPICS = [
    "NR-1 chapter 1.5 and Portaria MTE 1.419/2024 on psychosocial occupational risks",
    "Later MTE portarias, guides, and Q&A on GRO/PGR and the May 2026 enforcement window",
    "Anonymous workplace questionnaires: when they are allowed, and when they are not required",
    "LGPD limits on worker health data and psychosocial survey answers",
    "Peer-reviewed methods for assessing work-related psychosocial risk factors",
]

OFFICIAL_HOSTS = {
    "gov.br",
    "planalto.gov.br",
    "in.gov.br",
}

OFFICIAL_TYPES = {
    "official-norm",
    "official-guide",
    "official-qa",
}

# Sources that publish without peer review; papers from these are rejected.
PREPRINT_HOSTS = {
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "chemrxiv.org",
    "preprints.org",
    "ssrn.com",
    "papers.ssrn.com",
    "researchsquare.com",
    "osf.io",
    "zenodo.org",
}

# Hosts accepted as evidence of a real scholarly record when no DOI is supplied.
SCHOLARLY_HOSTS = {
    "doi.org",
    "dx.doi.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "sciencedirect.com",
    "springer.com",
    "link.springer.com",
    "nature.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "sagepub.com",
    "journals.sagepub.com",
    "mdpi.com",
    "frontiersin.org",
    "bmj.com",
    "thelancet.com",
    "jamanetwork.com",
    "nejm.org",
    "cambridge.org",
    "oup.com",
    "academic.oup.com",
    "acs.org",
    "pubs.acs.org",
    "rsc.org",
    "pubs.rsc.org",
    "plos.org",
    "journals.plos.org",
    "karger.com",
    "liebertpub.com",
    "scielo.br",
    "scielo.org",
    "elsevier.com",
    "iopscience.iop.org",
    "asme.org",
    "ascelibrary.org",
}

NON_PEER_REVIEWED_TYPES = {
    "preprint",
    "blog",
    "news",
    "press-release",
    "magazine",
    "thesis",
    "dissertation",
    "white-paper",
    "report",
    "conference-abstract",
    "patent",
}

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class Paper:
    title: str
    url: str
    journal: str = ""
    authors: str = ""
    year: int | None = None
    doi: str = ""
    category: str = "uncategorized"
    publication_type: str = ""
    peer_reviewed: bool = False
    confidence: float = 0.0
    summary: str = ""
    published: date | None = None

    def dedupe_key(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower()}"
        return f"url:{normalize_url(self.url)}"


@dataclass
class FilterOutcome:
    accepted: list[Paper] = field(default_factory=list)
    rejected: list[tuple[Paper, str]] = field(default_factory=list)


def utc_date(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_report_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def publication_cutoff(date_str: str, max_age_days: int) -> date:
    return parse_report_date(date_str) - timedelta(days=max_age_days)


def identity_keys(*, doi: str = "", url: str = "", title: str = "") -> set[str]:
    keys: set[str] = set()
    doi_text = (doi or "").strip().lower()
    if doi_text:
        keys.add(f"doi:{doi_text}")
    url_text = normalize_url(url)
    if url_text:
        keys.add(f"url:{url_text}")
    title_text = (title or "").strip().lower()
    if title_text:
        keys.add(f"title:{title_text}")
    return keys


def paper_identity_keys(paper: Paper) -> set[str]:
    return identity_keys(doi=paper.doi, url=paper.url, title=paper.title)


def record_identity_keys(item: dict[str, Any]) -> set[str]:
    return identity_keys(
        doi=str(item.get("doi") or ""),
        url=str(item.get("url") or ""),
        title=str(item.get("title") or ""),
    )


def discovered_paper_keys(records: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for item in records:
        keys |= record_identity_keys(item)
    return keys


def paper_to_dict(paper: Paper) -> dict[str, Any]:
    payload = dict(paper.__dict__)
    published = payload.get("published")
    if isinstance(published, date):
        payload["published"] = published.isoformat()
    return payload


def normalize_url(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    cleaned = re.sub(r"^https?://", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"^www\.", "", cleaned, flags=re.IGNORECASE).lower()


def url_host(url: str) -> str:
    return normalize_url(url).split("/", 1)[0]


def host_matches(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)


def format_known_papers_for_prompt(records: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in records:
        doi = str(item.get("doi") or "").strip()
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        ident = doi or url
        if not ident and not title:
            continue
        if title and ident:
            lines.append(f"        - {ident} — {title}")
        else:
            lines.append(f"        - {ident or title}")
    return "\n".join(lines)


def build_prompt(
    date_str: str,
    max_papers: int,
    min_confidence: float,
    *,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    known_papers: list[dict[str, Any]] | None = None,
) -> str:
    topics = "\n".join(f"        - {topic}" for topic in RESEARCH_TOPICS)
    cutoff = publication_cutoff(date_str, max_age_days)
    known_section = ""
    known_records = [item for item in (known_papers or []) if isinstance(item, dict)]
    known_block = format_known_papers_for_prompt(known_records)
    if known_block:
        known_section = f"""
        Previously reported — do NOT include these again (match by DOI, URL, or title):
{known_block}
"""

    return textwrap.dedent(
        f"""
        You are a research librarian building the "Weekly Law Report {date_str}" digest
        for an anonymous employee welfare questionnaire product in Brazil.

        Goal: find the most recent official instruments and peer-reviewed literature
        about psychosocial occupational risk management and anonymous worker
        questionnaires, across these areas:
{topics}

        Hard requirements — a source is only eligible if ALL of these hold:
        - It is either (a) an official Brazilian instrument or guidance
          (NR, Portaria, Diário Oficial, MTE guide or Q&A on gov.br / planalto.gov.br /
          in.gov.br; set publication_type to official-norm, official-guide, or official-qa
          and peer_reviewed to false) or (b) a peer-reviewed journal article.
        - Preprints, theses, patents, vendor blogs, press releases, conference abstracts
          and news articles are NOT eligible.
        - A journal article needs a resolvable DOI or a canonical publisher/index link.
          An official instrument needs its canonical gov.br, planalto.gov.br, or in.gov.br URL.
        - You verified the record actually exists; never invent a DOI, title, article number, or link.
        - It was published or officially updated in the past month only: on or after
          {cutoff.isoformat()} and on or before {date_str}. Year-only dates are not acceptable.
          If you cannot confirm a calendar date (YYYY-MM-DD) inside that window, omit the source.
{known_section}
        Reliability: assign each paper a `confidence` between 0 and 1 reflecting how sure
        you are that the record is real, peer-reviewed and correctly described. Report a low
        confidence instead of guessing. Papers below {min_confidence} will be discarded, and
        it is far better to return fewer papers than to return an unreliable one. Returning
        an empty list is an acceptable outcome.

        Return at most {max_papers} papers.

        Output format — reply with a single fenced ```json block and nothing else:

        ```json
        {{
          "generated_for": "{date_str}",
          "papers": [
            {{
              "title": "Full paper title",
              "authors": "First Author et al.",
              "journal": "Journal name",
              "year": 2026,
              "published": "2026-09-01",
              "doi": "10.1000/example",
              "url": "https://doi.org/10.1000/example",
              "category": "nr-1 | psychosocial | anonymity-lgpd | inspection | methods",
              "publication_type": "journal-article | official-norm | official-guide | official-qa",
              "peer_reviewed": true,
              "confidence": 0.93,
              "summary": "One or two sentences on the finding and why it matters."
            }}
          ]
        }}
        ```

        Do not modify any files in the repository and do not open a pull request.
        Your entire deliverable is the JSON block above.
        """
    ).strip()


def create_research_agent(
    *,
    cursor_api_key: str,
    model: str,
    repo_url: str,
    base_ref: str,
    prompt: str,
    run_name: str,
) -> dict[str, Any]:
    token = base64.b64encode(f"{cursor_api_key}:".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
    }
    payload: dict[str, Any] = {
        "name": run_name,
        "prompt": {"text": prompt},
        "model": {"id": model},
        "repos": [{"url": repo_url, "startingRef": base_ref}],
        "autoCreatePR": False,
    }
    return _http_json("POST", f"{CURSOR_API_BASE}/agents", headers=headers, payload=payload)


def get_run(*, cursor_api_key: str, agent_id: str, run_id: str) -> dict[str, Any]:
    token = base64.b64encode(f"{cursor_api_key}:".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
    }
    result = _http_json("GET", f"{CURSOR_API_BASE}/agents/{agent_id}/runs/{run_id}", headers=headers)
    if not isinstance(result, dict):
        raise ApiError(f"Unexpected Cursor run response: {type(result)}")
    return result


def wait_for_run(
    *,
    cursor_api_key: str,
    agent_id: str,
    run_id: str,
    poll_interval: int,
    timeout: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_status = ""
    while True:
        run = get_run(cursor_api_key=cursor_api_key, agent_id=agent_id, run_id=run_id)
        status = str(run.get("status") or "").upper()
        if status != last_status:
            log(f"Run {run_id} status: {status or 'UNKNOWN'}")
            last_status = status
        if status in TERMINAL_STATUSES:
            return run
        if time.monotonic() >= deadline:
            raise ApiError(f"Timed out after {timeout}s waiting for run {run_id} (last status: {status})")
        time.sleep(max(poll_interval, 1))


def extract_json_payload(text: str) -> dict[str, Any]:
    """Pull the JSON object out of an assistant reply that may wrap it in prose/fences."""
    if not text or not text.strip():
        raise ValueError("Agent returned an empty result")

    candidates: list[str] = [match.group(1) for match in JSON_BLOCK_PATTERN.finditer(text)]

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Could not find a JSON object in the agent result")


def _coerce_year(value: Any) -> int | None:
    try:
        year = int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return None
    return year if 1900 <= year <= 2200 else None


def _coerce_published(value: Any) -> date | None:
    """Parse a calendar publication date. Year-only values are rejected as too vague."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if re.match(r"^\d{4}$", text):
        return None
    if re.match(r"^\d{4}-\d{2}$", text):
        try:
            return datetime.strptime(text, "%Y-%m").date()
        except ValueError:
            return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    # Tolerate agents reporting confidence as a percentage.
    if confidence > 1.0:
        confidence = confidence / 100.0
    return max(0.0, min(1.0, confidence))


def parse_papers(payload: dict[str, Any]) -> list[Paper]:
    raw_papers = payload.get("papers")
    if not isinstance(raw_papers, list):
        raise ValueError("Agent JSON payload has no 'papers' list")

    papers: list[Paper] = []
    for raw in raw_papers:
        if not isinstance(raw, dict):
            continue
        doi = str(raw.get("doi") or "").strip()
        doi = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        published = _coerce_published(
            raw.get("published") or raw.get("publication_date") or raw.get("date")
        )
        year = _coerce_year(raw.get("year"))
        if year is None and published is not None:
            year = published.year
        papers.append(
            Paper(
                title=str(raw.get("title") or "").strip(),
                url=str(raw.get("url") or "").strip(),
                journal=str(raw.get("journal") or "").strip(),
                authors=str(raw.get("authors") or "").strip(),
                year=year,
                doi=doi,
                category=str(raw.get("category") or "uncategorized").strip().lower(),
                publication_type=str(raw.get("publication_type") or "").strip().lower(),
                peer_reviewed=bool(raw.get("peer_reviewed")),
                confidence=_coerce_confidence(raw.get("confidence")),
                summary=str(raw.get("summary") or "").strip(),
                published=published,
            )
        )
    return papers


def rejection_reason(
    paper: Paper,
    min_confidence: float,
    *,
    as_of: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    known_keys: set[str] | None = None,
) -> str | None:
    """Return why a paper is not publishable, or None when it passes every check."""
    if known_keys and paper_identity_keys(paper) & known_keys:
        return "already reported in a previous digest"
    if not paper.title:
        return "missing title"
    if not paper.url:
        return "missing link"
    if not re.match(r"^https?://", paper.url, flags=re.IGNORECASE):
        return "link is not a valid http(s) URL"
    host = url_host(paper.url)
    official = paper.publication_type in OFFICIAL_TYPES or host_matches(host, OFFICIAL_HOSTS)
    if host_matches(host, PREPRINT_HOSTS):
        return f"hosted on preprint/repository domain '{host}'"
    if official:
        if not paper.journal:
            return "missing issuing body"
    else:
        if not paper.peer_reviewed:
            return "not flagged as peer-reviewed"
        if paper.publication_type in NON_PEER_REVIEWED_TYPES:
            return f"publication type '{paper.publication_type}' is not peer-reviewed"
        if not paper.journal:
            return "missing journal name"
        has_valid_doi = bool(paper.doi) and bool(DOI_PATTERN.match(paper.doi))
        if not has_valid_doi and not host_matches(host, SCHOLARLY_HOSTS):
            return f"no valid DOI and '{host}' is not a recognised scholarly domain"

    if paper.confidence < min_confidence:
        return f"confidence {paper.confidence:.2f} below threshold {min_confidence:.2f}"

    as_of = as_of or datetime.now(timezone.utc).date()
    if paper.published is None:
        return (
            f"publication date missing or not specific "
            f"(need YYYY-MM-DD within the last {max_age_days} days)"
        )
    cutoff = as_of - timedelta(days=max_age_days)
    if paper.published < cutoff:
        return (
            f"published {paper.published.isoformat()} is older than {max_age_days} days "
            f"(cutoff {cutoff.isoformat()})"
        )
    if paper.published > as_of:
        return f"published {paper.published.isoformat()} is after the report date {as_of.isoformat()}"
    return None


def filter_reliable_papers(
    papers: list[Paper],
    min_confidence: float,
    *,
    as_of: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    known_keys: set[str] | None = None,
) -> FilterOutcome:
    outcome = FilterOutcome()
    seen: set[str] = set()
    as_of = as_of or datetime.now(timezone.utc).date()
    for paper in papers:
        reason = rejection_reason(
            paper,
            min_confidence,
            as_of=as_of,
            max_age_days=max_age_days,
            known_keys=known_keys,
        )
        if reason:
            outcome.rejected.append((paper, reason))
            continue
        key = paper.dedupe_key()
        if key in seen:
            outcome.rejected.append((paper, "duplicate of an earlier entry"))
            continue
        seen.add(key)
        outcome.accepted.append(paper)
    outcome.accepted.sort(key=lambda p: (-p.confidence, p.title.lower()))
    return outcome


def _render_accepted_sections(outcome: FilterOutcome) -> list[str]:
    lines: list[str] = []
    by_category: dict[str, list[Paper]] = {}
    for paper in outcome.accepted:
        by_category.setdefault(paper.category or "uncategorized", []).append(paper)

    for category in sorted(by_category):
        lines.append(f"## {category.title()}")
        lines.append("")
        for paper in by_category[category]:
            meta = " · ".join(
                part
                for part in (paper.journal, str(paper.year) if paper.year else "", paper.authors)
                if part
            )
            lines.append(f"- [{paper.title}]({paper.url})")
            if meta:
                lines.append(f"  - {meta}")
            if paper.published:
                lines.append(f"  - Published: {paper.published.isoformat()}")
            if paper.doi:
                lines.append(f"  - DOI: `{paper.doi}`")
            lines.append(f"  - Confidence: {paper.confidence:.2f}")
            if paper.summary:
                lines.append(f"  - {paper.summary}")
        lines.append("")
    return lines


def render_issue_body(date_str: str, outcome: FilterOutcome, *, agent_url: str = "") -> str:
    """Issue body carrying only papers that cleared every reliability check.

    Discarded candidates are deliberately reduced to a count: the issue must not
    surface links that failed verification.
    """
    count = len(outcome.accepted)
    lines = [
        f"{count} verified source{'s' if count != 1 else ''} cleared the reliability checks "
        f"for {date_str}.",
        "",
    ]
    lines.extend(_render_accepted_sections(outcome))

    if outcome.rejected:
        discarded = len(outcome.rejected)
        noun = "candidate was" if discarded == 1 else "candidates were"
        lines.append(
            f"_{discarded} further {noun} discarded (already reported, older than "
            "one month, or failing the official-source / peer-review checks)._"
        )
        lines.append("")

    if agent_url:
        lines.append(f"[View Cursor agent run]({agent_url})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_summary(date_str: str, outcome: FilterOutcome, *, agent_url: str = "") -> str:
    """Full diagnostic report for the job summary and archived artifact."""
    lines = [f"# Weekly Law Report {date_str}", ""]

    if not outcome.accepted:
        lines.append("No verified sources cleared the reliability checks today.")
        lines.append("")
    else:
        count = len(outcome.accepted)
        lines.append(f"{count} verified source{'s' if count != 1 else ''} passed the reliability checks.")
        lines.append("")
        lines.extend(_render_accepted_sections(outcome))

    if outcome.rejected:
        lines.append("<details><summary>Discarded as unreliable "
                     f"({len(outcome.rejected)})</summary>")
        lines.append("")
        for paper, reason in outcome.rejected:
            label = paper.title or paper.url or "(untitled entry)"
            lines.append(f"- {label} — {reason}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if agent_url:
        lines.append(f"[View Cursor agent run]({agent_url})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def issue_title(date_str: str) -> str:
    return f"[RESEARCH] NR-1 Welfare {date_str}"


def issue_title_candidates(date_str: str) -> list[str]:
    """Current and legacy titles so re-runs stay idempotent after the prefix change."""
    return [
        f"[RESEARCH] NR-1 Welfare {date_str}",
        f"NR-1 Welfare {date_str}",
    ]


def _github_headers(github_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def ensure_issue_labels(repo: str, github_token: str, labels: list[str]) -> None:
    """Create missing labels so issue creation does not 422 on unknown names."""
    headers = _github_headers(github_token)
    for name in labels:
        if not name.strip():
            continue
        url = f"{GITHUB_API_BASE}/repos/{repo}/labels/{urllib.parse.quote(name)}"
        try:
            _http_json("GET", url, headers=headers)
            continue
        except ApiError as exc:
            if exc.status != 404:
                raise
        color = "0E8A16" if name.strip().lower() == "research" else "5319E7"
        description = (
            "Research note for the team — not a coding task for the issue solver"
            if name.strip().lower() == "research"
            else "NR-1 welfare research digest"
        )
        _http_json(
            "POST",
            f"{GITHUB_API_BASE}/repos/{repo}/labels",
            headers=headers,
            payload={"name": name, "color": color, "description": description},
        )
        log(f"Created label `{name}`.")


def find_issue_by_title(
    repo: str,
    github_token: str,
    titles: list[str],
    *,
    max_pages: int = 2,
) -> dict[str, Any] | None:
    """Return an existing issue matching any known title for this digest."""
    wanted = {title.strip() for title in titles if title.strip()}
    for page in range(1, max_pages + 1):
        query = urllib.parse.urlencode(
            {"state": "all", "per_page": "100", "page": str(page), "sort": "created", "direction": "desc"}
        )
        result = _http_json(
            "GET",
            f"{GITHUB_API_BASE}/repos/{repo}/issues?{query}",
            headers=_github_headers(github_token),
        )
        if not isinstance(result, list):
            raise ApiError(f"Unexpected GitHub response for issues: {type(result)}")
        if not result:
            return None
        for item in result:
            if not isinstance(item, dict) or "pull_request" in item:
                continue
            if (item.get("title") or "").strip() in wanted:
                return item
        if len(result) < 100:
            return None
    return None


def create_github_issue(
    repo: str,
    github_token: str,
    *,
    title: str,
    body: str,
    labels: list[str],
) -> dict[str, Any]:
    ensure_issue_labels(repo, github_token, labels)
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    result = _http_json(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/issues",
        headers=_github_headers(github_token),
        payload=payload,
    )
    if not isinstance(result, dict):
        raise ApiError(f"Unexpected GitHub response creating issue: {type(result)}")
    return result


def publish_issue(
    *,
    repo: str,
    github_token: str,
    date_str: str,
    outcome: FilterOutcome,
    labels: list[str],
    agent_url: str = "",
) -> str:
    """Create the daily research issue and return its URL."""
    title = issue_title(date_str)
    existing = find_issue_by_title(repo, github_token, issue_title_candidates(date_str))
    if existing:
        url = str(existing.get("html_url") or "")
        log(f"Issue '{existing.get('title') or title}' already exists; leaving it untouched ({url})")
        return url

    issue = create_github_issue(
        repo,
        github_token,
        title=title,
        body=render_issue_body(date_str, outcome, agent_url=agent_url),
        labels=labels,
    )
    url = str(issue.get("html_url") or "")
    log(f"Created issue '{title}' -> {url}")
    return url


def _parse_github_datetime(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_research_digest_issue(item: dict[str, Any]) -> bool:
    labels = {
        str(label.get("name") or "").strip().lower()
        for label in item.get("labels", [])
        if isinstance(label, dict)
    }
    if labels & RESEARCH_CLEANUP_LABELS:
        return True
    title = str(item.get("title") or "").lower()
    return any(marker in title for marker in RESEARCH_CLEANUP_TITLE_MARKERS)


def close_stale_research_issues(
    *,
    repo: str,
    github_token: str,
    older_than_days: int,
    dry_run: bool = False,
) -> int:
    """Close open research digests older than the retention window. Returns closed count."""
    if older_than_days < 1:
        raise ValueError("older_than_days must be >= 1")

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    headers = _github_headers(github_token)
    closed = 0
    page = 1

    while True:
        query = urllib.parse.urlencode(
            {
                "state": "open",
                "per_page": "100",
                "page": str(page),
                "sort": "created",
                "direction": "asc",
            }
        )
        result = _http_json(
            "GET",
            f"{GITHUB_API_BASE}/repos/{repo}/issues?{query}",
            headers=headers,
        )
        if not isinstance(result, list) or not result:
            break

        for item in result:
            if not isinstance(item, dict) or "pull_request" in item:
                continue
            if not is_research_digest_issue(item):
                continue
            created = _parse_github_datetime(str(item.get("created_at") or ""))
            if created is None or created > cutoff:
                continue

            number = int(item["number"])
            title = str(item.get("title") or "").strip()
            age_days = (datetime.now(timezone.utc) - created).days
            if dry_run:
                log(f"[DRY RUN] Would close stale research issue #{number} ({age_days}d): {title}")
                closed += 1
                continue

            comment = (
                f"Auto-closed: this research digest is older than {older_than_days} days "
                f"(created {created.date().isoformat()}, ~{age_days} days ago). "
                "Weekly research retention keeps the issue list focused on recent digests."
            )
            _http_json(
                "POST",
                f"{GITHUB_API_BASE}/repos/{repo}/issues/{number}/comments",
                headers=headers,
                payload={"body": comment},
            )
            _http_json(
                "PATCH",
                f"{GITHUB_API_BASE}/repos/{repo}/issues/{number}",
                headers=headers,
                payload={"state": "closed", "state_reason": "not_planned"},
            )
            log(f"Closed stale research issue #{number} ({age_days}d): {title}")
            closed += 1

        if len(result) < 100:
            break
        page += 1

    log(f"Stale research cleanup: closed {closed} issue(s) older than {older_than_days} day(s).")
    return closed


def write_outputs(
    *,
    date_str: str,
    summary_markdown: str,
    outcome: FilterOutcome,
    output_dir: Path | None,
) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(summary_markdown)
        log(f"Wrote job summary to {summary_path}")

    if output_dir is None:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{date_str}_law_research.md").write_text(summary_markdown, encoding="utf-8")
    payload = {
        "title": f"Weekly Law Report {date_str}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": [paper_to_dict(paper) for paper in outcome.accepted],
        "rejected": [
            {"paper": paper_to_dict(paper), "reason": reason} for paper, reason in outcome.rejected
        ],
    }
    (output_dir / f"{date_str}_law_research.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    log(f"Wrote report files to {output_dir}")


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"updated_at": "", "papers": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {"updated_at": "", "papers": raw}
    if not isinstance(raw, dict):
        raise ValueError(f"Catalog {path} is not a JSON object or list")
    papers = raw.get("papers", [])
    if not isinstance(papers, list):
        raise ValueError(f"Catalog {path} has no papers list")
    return raw


def write_catalog(path: Path, catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def upsert_discovered_papers(
    path: Path,
    papers: list[Paper],
    *,
    seen_on: str,
) -> int:
    catalog = load_catalog(path)
    records = list(catalog.get("papers") or [])
    keys = discovered_paper_keys(records)
    added = 0
    for paper in papers:
        if paper_identity_keys(paper) & keys:
            continue
        records.append(
            {
                "title": paper.title,
                "url": paper.url,
                "doi": paper.doi,
                "journal": paper.journal,
                "authors": paper.authors,
                "year": paper.year,
                "published": paper.published.isoformat() if paper.published else "",
                "category": paper.category,
                "first_seen": seen_on,
            }
        )
        keys |= paper_identity_keys(paper)
        added += 1
    if added:
        catalog["papers"] = records
        catalog["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_catalog(path, catalog)
    return added


def run_agent_and_collect(
    args: argparse.Namespace,
    cursor_api_key: str,
    date_str: str,
    known_papers: list[dict[str, Any]],
) -> tuple[list[Paper], str]:
    prompt = build_prompt(
        date_str,
        args.max_papers,
        args.min_confidence,
        max_age_days=args.max_age_days,
        known_papers=known_papers,
    )
    run_name = f"Weekly Law Report {date_str}"

    response = create_research_agent(
        cursor_api_key=cursor_api_key,
        model=args.model,
        repo_url=args.repo_url,
        base_ref=args.base_ref,
        prompt=prompt,
        run_name=run_name,
    )
    if not isinstance(response, dict):
        raise ApiError(f"Unexpected Cursor response: {type(response)}")

    agent = response.get("agent") if isinstance(response.get("agent"), dict) else {}
    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    agent_id = str(agent.get("id") or response.get("id") or "")
    run_id = str(run.get("id") or agent.get("latestRunId") or "")
    if not agent_id or not run_id:
        raise ApiError(f"Cursor did not return agent/run ids: {json.dumps(response)[:2000]}")

    agent_url = str(agent.get("url") or response.get("url") or f"https://cursor.com/agents/{agent_id}")
    log(f"Launched agent {agent_id} (run {run_id}) -> {agent_url}")

    final_run = wait_for_run(
        cursor_api_key=cursor_api_key,
        agent_id=agent_id,
        run_id=run_id,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )
    status = str(final_run.get("status") or "").upper()
    if status != "FINISHED":
        raise ApiError(f"Run {run_id} ended with status {status}")

    payload = extract_json_payload(str(final_run.get("result") or ""))
    return parse_papers(payload), agent_url


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect NR-1 psychosocial and questionnaire sources via a Cursor cloud agent."
    )
    parser.add_argument("--repo-url", required=True, help="Git repo URL the agent starts from")
    parser.add_argument("--repo", default=None, help="owner/repo that receives the weekly paper report issue")
    parser.add_argument("--base-ref", default="main", help="Base branch for the agent workspace")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Cursor model id")
    parser.add_argument("--date", default=None, help="Override the report date (YYYY-MM-DD)")
    parser.add_argument("--max-papers", type=int, default=DEFAULT_MAX_PAPERS)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Reject papers whose reported confidence is below this value",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help="Only accept papers published within this many days of the report date",
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG_PATH),
        help="JSON file of papers already posted; those DOIs/URLs are skipped",
    )
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output-dir", default=None, help="Directory for the markdown/JSON report")
    parser.add_argument(
        "--result-file",
        default=None,
        help="Read the agent JSON result from a file instead of calling Cursor (testing)",
    )
    parser.add_argument(
        "--issue-label",
        action="append",
        default=None,
        help=f"Label applied to the issue (repeatable). Defaults to: {', '.join(DEFAULT_ISSUE_LABELS)}",
    )
    parser.add_argument(
        "--no-issue",
        action="store_true",
        help="Skip GitHub issue creation and only write the report files",
    )
    parser.add_argument(
        "--cleanup-older-than-days",
        type=int,
        default=DEFAULT_CLEANUP_OLDER_THAN_DAYS,
        help="Close open research digests older than this many days (0 disables cleanup)",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only close stale research issues; skip research gathering",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the prompt and exit")
    args = parser.parse_args()

    issue_labels = list(args.issue_label if args.issue_label is not None else DEFAULT_ISSUE_LABELS)

    date_str = utc_date(args.date)
    output_dir = Path(args.output_dir) if args.output_dir else None
    catalog_path = Path(args.catalog)

    if args.cleanup_older_than_days < 0:
        log("--cleanup-older-than-days must be >= 0", error=True)
        return 2
    if args.max_age_days < 1:
        log("--max-age-days must be >= 1", error=True)
        return 2

    try:
        catalog = load_catalog(catalog_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        log(f"Failed to load paper catalog {catalog_path}: {exc}", error=True)
        return 2
    known_papers = [item for item in catalog.get("papers", []) if isinstance(item, dict)]
    known_keys = discovered_paper_keys(known_papers)
    log(f"Loaded {len(known_papers)} previously reported paper(s) from {catalog_path}.")

    github_token = os.environ.get("GITHUB_TOKEN")
    if args.cleanup_older_than_days > 0:
        if not args.repo:
            log("--repo is required for research issue cleanup", error=True)
            return 2
        if not github_token:
            log("Missing required env var: GITHUB_TOKEN (needed to close stale issues)", error=True)
            return 2
        try:
            close_stale_research_issues(
                repo=args.repo,
                github_token=github_token,
                older_than_days=args.cleanup_older_than_days,
                dry_run=args.dry_run,
            )
        except (ApiError, ValueError) as exc:
            log(f"Stale research cleanup failed: {exc}", error=True)
            return 1

    if args.cleanup_only:
        return 0

    if args.dry_run:
        log(f"[DRY RUN] Would launch agent 'Weekly Law Report {date_str}' with prompt:\n")
        log(
            build_prompt(
                date_str,
                args.max_papers,
                args.min_confidence,
                max_age_days=args.max_age_days,
                known_papers=known_papers,
            )
        )
        return 0

    agent_url = ""
    if args.result_file:
        payload = extract_json_payload(Path(args.result_file).read_text(encoding="utf-8"))
        papers = parse_papers(payload)
    else:
        cursor_api_key = os.environ.get("CURSOR_API_KEY")
        if not cursor_api_key:
            log("Missing required env var: CURSOR_API_KEY", error=True)
            return 2
        try:
            papers, agent_url = run_agent_and_collect(args, cursor_api_key, date_str, known_papers)
        except (ApiError, ValueError) as exc:
            log(f"Weekly Law Report {date_str} failed: {exc}", error=True)
            return 1

    as_of = parse_report_date(date_str)
    outcome = filter_reliable_papers(
        papers,
        args.min_confidence,
        as_of=as_of,
        max_age_days=args.max_age_days,
        known_keys=known_keys,
    )
    summary_markdown = render_summary(date_str, outcome, agent_url=agent_url)
    write_outputs(
        date_str=date_str,
        summary_markdown=summary_markdown,
        outcome=outcome,
        output_dir=output_dir,
    )

    if outcome.accepted:
        added = upsert_discovered_papers(catalog_path, outcome.accepted, seen_on=date_str)
        log(f"Catalog {catalog_path}: added {added} newly accepted paper(s).")

    log(
        f"Weekly Law Report {date_str}: {len(outcome.accepted)} accepted, "
        f"{len(outcome.rejected)} discarded."
    )

    if args.no_issue or not args.repo:
        return 0

    if not outcome.accepted:
        # Requirement: publish links only when they are reliable. An empty digest
        # would be noise, so no issue is opened today.
        log("No reliable papers today; skipping issue creation.")
        return 0

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        log("Missing required env var: GITHUB_TOKEN (needed to open the issue)", error=True)
        return 2

    try:
        publish_issue(
            repo=args.repo,
            github_token=github_token,
            date_str=date_str,
            outcome=outcome,
            labels=issue_labels,
            agent_url=agent_url,
        )
    except ApiError as exc:
        log(f"Failed to publish 'Weekly Law Report {date_str}' issue: {exc}", error=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
