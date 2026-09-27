#!/usr/bin/env python3
"""
Dispatch one Cursor cloud agent for a single GitHub issue trigger.

Triggers:
- `solve`: the issue was labeled `solve`
- `correction`: a comment whose body starts with `[CORRECTION]`
- `post`: a `[POST]` comment on an issue labeled `law-research`

The launched agent is instructed to:
- assess change complexity on a 1–5 scale
- commit complexity 1–3 directly on the base branch
- open a pull request only for complexity 4–5
- include validation notes
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
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


GITHUB_API_BASE = "https://api.github.com"
CURSOR_API_BASE = "https://api.cursor.com/v1"
MAX_LAUNCH_ATTEMPTS = 5
MAX_RETRY_WAIT_SECONDS = 180
DEFAULT_RETRY_WAIT_SECONDS = 60
SKIP_LABELS = frozenset({"research", "[research]", "law-research"})
RESEARCH_TITLE_MARKER = "[research]"
RESEARCH_LABEL = "research"
SOLVE_LABEL = "solve"
LAW_RESEARCH_LABEL = "law-research"
LAW_RESEARCH_TITLE_MARKER = "nr-1 welfare"
CORRECTION_PREFIX = "[CORRECTION]"
POST_PREFIX = "[POST]"
TRIGGERS = ("solve", "correction", "post")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s)<>\"']+")
DOI_TICK_RE = re.compile(r"DOI:\s*`([^`]+)`", re.IGNORECASE)


@dataclass
class Issue:
    number: int
    title: str
    body: str
    html_url: str
    labels: list[str]


@dataclass
class IssueComment:
    id: int
    body: str
    html_url: str
    user: str = ""


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retryable: bool = False,
        retry_after: int | None = None,
        body: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.retry_after = retry_after
        self.body = body


def log(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(message, file=stream, flush=True)


def _walk_values(value: Any) -> Any:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_values(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)


def _parse_retry_after(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        seconds = int(float(raw.strip()))
    except ValueError:
        return None
    return max(1, seconds)


def _error_hints(payload: Any) -> tuple[bool, int | None]:
    retryable = False
    retry_after: int | None = None
    for node in _walk_values(payload):
        if node.get("isRetryable") is True or node.get("is_retryable") is True:
            retryable = True
        extra = node.get("additionalInfo") or node.get("additional_info") or {}
        if isinstance(extra, dict):
            parsed = _parse_retry_after(str(extra.get("retryAfter") or extra.get("retry_after") or ""))
            if parsed is not None:
                retry_after = parsed
        parsed = _parse_retry_after(str(node.get("retryAfter") or node.get("retry_after") or ""))
        if parsed is not None:
            retry_after = parsed
        if str(node.get("error") or "") == "ERROR_RATE_LIMITED":
            retryable = True
        if str(node.get("code") or "") in {"resource_exhausted", "rate_limited"}:
            retryable = True
    return retryable, retry_after


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    debug: bool = False,
) -> dict[str, Any] | list[Any]:
    data = None
    request_headers = headers.copy() if headers else {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, method=method, headers=request_headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            if debug:
                log(f"{method} {url} -> HTTP {resp.status}")
                log(f"Cursor response body:\n{raw[:8000] if raw else '(empty)'}")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed: Any = None
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = None
        retryable, retry_after = _error_hints(parsed)
        header_retry = _parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
        if header_retry is not None:
            retry_after = header_retry
        if exc.code in {429, 503}:
            retryable = True
            retry_after = retry_after or DEFAULT_RETRY_WAIT_SECONDS
        raise ApiError(
            f"{method} {url} failed ({exc.code}): {body}",
            status=exc.code,
            retryable=retryable,
            retry_after=retry_after,
            body=body,
        ) from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"{method} {url} failed: {exc.reason}", retryable=True) from exc


def issue_labels(issue: Issue) -> set[str]:
    return {label.strip().lower() for label in issue.labels}


def comment_has_prefix(body: str, prefix: str) -> bool:
    """True when the comment starts with the command prefix (ignoring leading space)."""
    return body.lstrip().upper().startswith(prefix.upper())


def extract_source_links(body: str) -> list[str]:
    """URLs and DOIs from a research-issue description, in first-seen order."""
    found: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        cleaned = url.strip().rstrip(").,;")
        if not cleaned:
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        found.append(cleaned)

    text = body or ""
    for match in MARKDOWN_LINK_RE.finditer(text):
        add(match.group(2))
    for match in BARE_URL_RE.finditer(text):
        add(match.group(0))
    for match in DOI_TICK_RE.finditer(text):
        add(f"https://doi.org/{match.group(1).strip()}")
    return found


def _source_links_block(links: list[str]) -> str:
    if not links:
        return (
            "Source links found in the research issue:\n"
            "- (none parsed — search the description again; if a URL or DOI is "
            "present, you must still use it)"
        )
    listed = "\n".join(f"- {url}" for url in links)
    return "Source links found in the research issue (open these before writing):\n" + listed


def skip_reason(issue: Issue, *, trigger: str = "solve") -> str | None:
    """Return why this issue should not be dispatched for the given trigger."""
    labels = issue_labels(issue)
    if trigger == "correction":
        return None
    if trigger == "post":
        if LAW_RESEARCH_LABEL not in labels:
            return f"missing `{LAW_RESEARCH_LABEL}` label"
        return None
    if trigger != "solve":
        return f"unknown trigger `{trigger}`"

    matched = labels & SKIP_LABELS
    if matched:
        return f"label {sorted(matched)[0]}"
    title_lower = issue.title.lower()
    if RESEARCH_TITLE_MARKER in title_lower:
        return "title marker [RESEARCH]"
    if LAW_RESEARCH_TITLE_MARKER in title_lower:
        return "title marker NR-1 Welfare"
    if SOLVE_LABEL not in labels:
        return f"missing `{SOLVE_LABEL}` label"
    return None


def ensure_research_label(repo: str, headers: dict[str, str]) -> None:
    url = f"{GITHUB_API_BASE}/repos/{repo}/labels/{urllib.parse.quote(RESEARCH_LABEL)}"
    try:
        _http_json("GET", url, headers=headers)
        return
    except ApiError as exc:
        if exc.status != 404:
            raise
    _http_json(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/labels",
        headers=headers,
        payload={
            "name": RESEARCH_LABEL,
            "color": "0E8A16",
            "description": "Research note for the team — not a coding task for the issue solver",
        },
    )
    log(f"Created label `{RESEARCH_LABEL}`.")


def ensure_solve_label(repo: str, headers: dict[str, str]) -> None:
    url = f"{GITHUB_API_BASE}/repos/{repo}/labels/{urllib.parse.quote(SOLVE_LABEL)}"
    try:
        _http_json("GET", url, headers=headers)
        return
    except ApiError as exc:
        if exc.status != 404:
            raise
    _http_json(
        "POST",
        f"{GITHUB_API_BASE}/repos/{repo}/labels",
        headers=headers,
        payload={
            "name": SOLVE_LABEL,
            "color": "5319E7",
            "description": "Queue this issue for the AI agent to implement",
        },
    )
    log(f"Created label `{SOLVE_LABEL}`.")


def stamp_research_label(repo: str, issue: Issue, headers: dict[str, str]) -> None:
    """Promote research title markers into the durable `research` label."""
    if RESEARCH_LABEL in {label.strip().lower() for label in issue.labels}:
        return
    title_lower = issue.title.lower()
    if RESEARCH_TITLE_MARKER not in title_lower and LAW_RESEARCH_TITLE_MARKER not in title_lower:
        return
    try:
        ensure_research_label(repo, headers)
        _http_json(
            "POST",
            f"{GITHUB_API_BASE}/repos/{repo}/issues/{issue.number}/labels",
            headers=headers,
            payload={"labels": [RESEARCH_LABEL]},
        )
        log(f"Stamped `{RESEARCH_LABEL}` on issue #{issue.number}.")
    except ApiError as exc:
        log(f"Could not stamp `{RESEARCH_LABEL}` on issue #{issue.number}: {exc}", error=True)


def github_headers(github_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def parse_issue(item: dict[str, Any]) -> Issue | None:
    if "pull_request" in item:
        return None
    return Issue(
        number=int(item["number"]),
        title=item.get("title", "").strip(),
        body=(item.get("body") or "").strip(),
        html_url=item.get("html_url", ""),
        labels=[label.get("name", "") for label in item.get("labels", []) if isinstance(label, dict)],
    )


def fetch_issue_by_number(repo: str, github_token: str, number: int) -> Issue | None:
    headers = github_headers(github_token)
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{number}"
    result = _http_json("GET", url, headers=headers)
    if not isinstance(result, dict):
        raise ApiError(f"Unexpected GitHub response for issue #{number}: {type(result)}")
    return parse_issue(result)


def fetch_issue_comment(repo: str, github_token: str, comment_id: int) -> IssueComment:
    headers = github_headers(github_token)
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/comments/{comment_id}"
    result = _http_json("GET", url, headers=headers)
    if not isinstance(result, dict):
        raise ApiError(f"Unexpected GitHub response for comment #{comment_id}: {type(result)}")
    user = result.get("user") if isinstance(result.get("user"), dict) else {}
    return IssueComment(
        id=int(result.get("id") or comment_id),
        body=(result.get("body") or "").strip(),
        html_url=str(result.get("html_url") or ""),
        user=str(user.get("login") or ""),
    )


def _issue_metadata_block(issue: Issue) -> str:
    labels = ", ".join(issue.labels) if issue.labels else "none"
    issue_body = issue.body if issue.body else "(no description provided)"
    return textwrap.dedent(
        f"""
        - URL: {issue.html_url}
        - Title: {issue.title}
        - Labels: {labels}
        - Description:
        {issue_body}
        """
    ).strip()


def _comment_block(comment: IssueComment, prefix: str) -> str:
    return textwrap.dedent(
        f"""
        - Prefix required: {prefix}
        - Author: {comment.user or "unknown"}
        - URL: {comment.html_url or "(no comment URL)"}
        - Body:
        {comment.body or "(empty comment)"}
        """
    ).strip()


def _delivery_rules(
    issue: Issue,
    repo: str,
    base_ref: str,
    *,
    pr_title_prefix: str,
    close_issue: bool,
) -> str:
    owner = repo.split("/", 1)[0]
    related = (
        f"7) Closes #{issue.number}"
        if close_issue
        else (
            f"7) Related to #{issue.number} — do not close this research digest; "
            "other papers may still be posted later."
        )
    )
    return textwrap.dedent(
        f"""
        Complexity assessment (required):
        Before you implement, rate the change from 1 to 5 and keep that rating
        throughout the run. Comment the rating on issue #{issue.number}.

        1 — Trivial: typo, copy, comment, or one-line config/docs.
        2 — Simple: localized change in a few files, existing pattern, low risk.
        3 — Moderate: several files or straightforward logic; no architecture shift.
        4 — Complex: cross-stack, API/schema, security, or behavior that needs review.
        5 — Major: architecture, migration, large refactor, or uncertain design.

        Delivery rules (follow exactly):
        - Complexity 1–3: commit the finished change on `{base_ref}` itself.
          Check out `{base_ref}`, make one ordinary commit, and push `{base_ref}`.
          Do not open a pull request. Do not finish on a `cursor/*` branch.
          Do not create a merge commit. A pull request for this rating is wrong.
        - Complexity 4–5: open a pull request and do NOT merge it.
          Title format: "{pr_title_prefix}(issue #{issue.number}): <short summary>"
          Request a review from `{owner}` so they receive GitHub's email with
          the PR title. Body sections, in order:
          1) Complexity (N/5, one-sentence justification)
          2) Summary
          3) Root Cause
          4) Changes Made
          5) Validation (tests/manual checks)
          6) Risks / Follow-ups
          {related}
          Mention changed files and why each was changed.

        Before finishing:
        - Run relevant checks/tests for changed components.
        - Ensure formatting/lint expectations still pass for touched files.
        - Comment on issue #{issue.number} with the complexity rating and
          whether you merged to `{base_ref}` or opened a PR.
        """
    ).strip()


def build_prompt(
    issue: Issue,
    repo: str,
    base_ref: str,
    *,
    trigger: str = "solve",
    comment: IssueComment | None = None,
) -> str:
    metadata = _issue_metadata_block(issue)
    if trigger == "correction":
        if comment is None:
            raise ValueError("correction trigger requires a comment")
        task = "\n\n".join(
            [
                textwrap.dedent(
                    f"""
                    You are working on repository {repo}.
                    Apply a CORRECTION on GitHub issue #{issue.number}.
                    The delivery rules decide whether this lands on {base_ref}
                    or in a pull request. Do not default to a pull request.

                    Constraints:
                    - The triggering comment is the task. Do not re-open the original
                      issue scope unless the correction explicitly says so.
                    - Touch only code needed for this correction.
                    - Keep scope focused and minimal.
                    - Add or update tests when feasible.
                    - Base branch: {base_ref}.
                    """
                ).strip(),
                "Triggering comment:\n" + _comment_block(comment, CORRECTION_PREFIX),
                "Original issue (context only):\n" + metadata,
            ]
        )
        rules = _delivery_rules(
            issue, repo, base_ref, pr_title_prefix="fix", close_issue=True
        )
    elif trigger == "post":
        if comment is None:
            raise ValueError("post trigger requires a comment")
        source_links = extract_source_links(issue.body)
        task = "\n\n".join(
            [
                textwrap.dedent(
                    f"""
                    You are working on repository {repo}.
                    File a briefing for the named source(s) from this NR-1 welfare
                    research digest (GitHub issue #{issue.number}).

                    Constraints:
                    - The triggering [POST] comment names which source to brief.
                    - Do not treat the digest as a coding bug to "solve".
                    - Do not brief sources that the comment does not name.
                    - Do not close issue #{issue.number}; other sources may still be posted.
                    - Do not add unrelated site changes.
                    - Base branch: {base_ref}.

                    Read the sources before you write (required):
                    - The issue description is only a catalog. Never paraphrase its
                      one-line summary as the briefing.
                    - Open every source URL for the selected item. Follow through to
                      the official text (NR-1, Portaria, Diário Oficial, MTE guide)
                      or the publisher page and PDF when it is a paper.
                    - Take notes on what the instrument requires, who it binds, dates
                      of effect, anonymity and LGPD limits, and what it does not require.
                    - If a paper is paywalled, use the abstract plus any open
                      tables, say that the full text was not open, and still write
                      the deepest briefing those sources allow. Keep the original link.
                    """
                ).strip(),
                "Triggering comment:\n" + _comment_block(comment, POST_PREFIX),
                _source_links_block(source_links),
                textwrap.dedent(
                    """
                    Briefing depth (required — this is the main deliverable):
                    Write an original Portuguese briefing for people building an
                    anonymous employee welfare questionnaire under the updated NR-1
                    (psychosocial occupational risks). It must explain the source,
                    not tease it.

                    Do NOT:
                    - Invent article numbers, dates, or duties that are not in the source.
                    - Write a one-paragraph resumo and stop.
                    - Add product marketing copy.
                    - Treat a questionnaire as mandatory if the source says it is optional.

                    Do:
                    - Add one markdown file under `docs/research/`.
                    - Filename: a short ASCII slug plus `.md`.
                    - Start with a YAML-less title heading and the source link.
                    - Sections, in order, as `##` headings in Portuguese:
                      1) **Por que importa** — what changes for an employer in Brazil
                      2) **O que o texto exige** — duties, dates, who is covered
                      3) **Anonimato e dados** — what it says about anonymous
                         questionnaires, worker participation, and sensitive data
                      4) **O que não exige** — limits, including that a questionnaire
                         is a method, not the whole GRO/PGR
                      5) **Leitura para o produto** — what a software tool may and
                         may not claim
                      6) **Fonte** — clickable markdown link

                    Publishing rules:
                    - This [POST] comment is human approval for the named source only.
                    - Always include every URL or DOI given in the issue description.
                    - Links must be clickable markdown: `[texto](https://…)`.
                    - Do not create blog, news, or course JSON. The site has no
                      content catalog yet.
                    """
                ).strip(),
                "Research digest (catalog only — titles and links, not the article copy):\n"
                + metadata,
            ]
        )
        rules = _delivery_rules(
            issue, repo, base_ref, pr_title_prefix="feat", close_issue=False
        )
    else:
        task = "\n\n".join(
            [
                textwrap.dedent(
                    f"""
                    You are working on repository {repo}.
                    Solve GitHub issue #{issue.number}.
                    The delivery rules decide whether this lands on {base_ref}
                    or in a pull request. Do not default to a pull request.

                    Constraints:
                    - Touch only code relevant to issue #{issue.number}.
                    - Keep scope focused and minimal.
                    - Add or update tests when feasible.
                    - Base branch: {base_ref}.
                    """
                ).strip(),
                "Issue (this labeled `solve` issue is the task):\n" + metadata,
            ]
        )
        rules = _delivery_rules(
            issue, repo, base_ref, pr_title_prefix="fix", close_issue=True
        )
    return f"{task}\n\n{rules}"


def create_cursor_agent(
    *,
    cursor_api_key: str,
    model: str,
    repo_url: str,
    base_ref: str,
    prompt: str,
    run_name: str,
    skip_reviewer_request: bool,
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
        "skipReviewerRequest": skip_reviewer_request,
    }
    return _http_json(
        "POST",
        f"{CURSOR_API_BASE}/agents",
        headers=headers,
        payload=payload,
        debug=True,
    )


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            text = str(value).strip()
            if text:
                return text
    return None


def agent_identity(response: dict[str, Any]) -> tuple[str | None, str | None]:
    agent = response.get("agent") if isinstance(response.get("agent"), dict) else {}
    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    target = agent.get("target") if isinstance(agent.get("target"), dict) else response.get("target")
    if not isinstance(target, dict):
        target = {}

    agent_id = _first_text(
        agent.get("id"),
        response.get("id"),
        response.get("agentId"),
        response.get("agent_id"),
        run.get("agentId"),
        run.get("agent_id"),
    )
    agent_url = _first_text(
        agent.get("url"),
        target.get("url"),
        response.get("url"),
        target.get("prUrl"),
        run.get("url"),
    )
    if agent_id and not agent_url:
        agent_url = f"https://cursor.com/agents/{agent_id}"
    return agent_id, agent_url


def _sleep(seconds: int, reason: str) -> None:
    wait = min(max(seconds, 1), MAX_RETRY_WAIT_SECONDS)
    log(f"Waiting {wait}s ({reason})")
    time.sleep(wait)


def create_cursor_agent_with_retry(**kwargs: Any) -> dict[str, Any]:
    last_error: ApiError | None = None
    for attempt in range(1, MAX_LAUNCH_ATTEMPTS + 1):
        try:
            response = create_cursor_agent(**kwargs)
            if not isinstance(response, dict):
                raise ApiError(f"Unexpected Cursor response: {type(response)}")
            return response
        except ApiError as exc:
            last_error = exc
            if not exc.retryable or attempt == MAX_LAUNCH_ATTEMPTS:
                raise
            wait = exc.retry_after or min(DEFAULT_RETRY_WAIT_SECONDS * attempt, MAX_RETRY_WAIT_SECONDS)
            log(
                f"Retryable Cursor error on attempt {attempt}/{MAX_LAUNCH_ATTEMPTS} "
                f"(status={exc.status}): {exc}",
                error=True,
            )
            _sleep(wait, "Cursor asked us to retry")
    assert last_error is not None
    raise last_error


def _run_name(trigger: str, issue: Issue) -> str:
    title = issue.title[:80]
    if trigger == "correction":
        return f"Correction #{issue.number}: {title}"
    if trigger == "post":
        return f"Post #{issue.number}: {title}"
    return f"Issue #{issue.number}: {title}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch a Cursor cloud agent for one GitHub issue trigger."
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--repo-url", required=True, help="Git clone URL, e.g. https://github.com/org/repo")
    parser.add_argument("--base-ref", required=True, help="Base branch used by cloud agents")
    parser.add_argument("--issue-number", type=int, required=True, help="Issue number that triggered the run")
    parser.add_argument(
        "--trigger",
        choices=TRIGGERS,
        default="solve",
        help="solve | correction | post",
    )
    parser.add_argument(
        "--comment-id",
        type=int,
        default=0,
        help="Issue comment ID (required for correction and post)",
    )
    parser.add_argument("--model", default="composer-2.5", help="Cursor model id")
    parser.add_argument("--dry-run", action="store_true", help="Only print planned operations")
    parser.add_argument(
        "--skip-reviewer-request",
        action="store_true",
        help="Set Cursor skipReviewerRequest=true when opening PRs",
    )
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    cursor_api_key = os.environ.get("CURSOR_API_KEY")
    if not github_token:
        log("Missing required env var: GITHUB_TOKEN", error=True)
        return 2
    if not cursor_api_key and not args.dry_run:
        log("Missing required env var: CURSOR_API_KEY", error=True)
        return 2

    if args.issue_number < 1:
        log("--issue-number must be >= 1", error=True)
        return 2
    if args.trigger in {"correction", "post"} and args.comment_id < 1:
        log(f"--comment-id is required for trigger `{args.trigger}`", error=True)
        return 2

    try:
        headers = github_headers(github_token)
        if args.trigger == "solve":
            ensure_solve_label(args.repo, headers)
        issue = fetch_issue_by_number(args.repo, github_token, args.issue_number)
        if issue is None:
            log(f"Issue #{args.issue_number} is a pull request, not an issue.", error=True)
            return 1
        comment: IssueComment | None = None
        if args.comment_id:
            comment = fetch_issue_comment(args.repo, github_token, args.comment_id)
    except ApiError as exc:
        log(f"Failed fetching issue trigger: {exc}", error=True)
        return 1

    if args.trigger == "correction":
        if comment is None or not comment_has_prefix(comment.body, CORRECTION_PREFIX):
            log(
                f"Skipping issue #{issue.number}: comment does not start with {CORRECTION_PREFIX}",
            )
            return 0
    elif args.trigger == "post":
        if comment is None or not comment_has_prefix(comment.body, POST_PREFIX):
            log(f"Skipping issue #{issue.number}: comment does not start with {POST_PREFIX}")
            return 0

    reason = skip_reason(issue, trigger=args.trigger)
    if reason:
        log(f"Skipping issue #{issue.number} ({reason}): {issue.title}")
        if args.trigger == "solve" and "title marker" in reason:
            stamp_research_label(args.repo, issue, headers)
        return 0

    prompt = build_prompt(
        issue,
        args.repo,
        args.base_ref,
        trigger=args.trigger,
        comment=comment,
    )
    run_name = _run_name(args.trigger, issue)
    log(f"Trigger `{args.trigger}` on issue #{issue.number}: {issue.title}")

    if args.dry_run:
        log(f"[DRY RUN] Would launch agent for issue #{issue.number}: {issue.title}")
        log(f"[DRY RUN] Prompt preview:\n{prompt[:2000]}")
        return 0

    try:
        response = create_cursor_agent_with_retry(
            cursor_api_key=cursor_api_key or "",
            model=args.model,
            repo_url=args.repo_url,
            base_ref=args.base_ref,
            prompt=prompt,
            run_name=run_name,
            skip_reviewer_request=args.skip_reviewer_request,
        )
    except ApiError as exc:
        log(f"Issue #{issue.number} launch failed: {exc}", error=True)
        return 1

    log(f"Issue #{issue.number} Cursor payload keys: {sorted(response.keys())}")
    agent_id, agent_url = agent_identity(response)
    if not agent_id:
        log(
            f"Issue #{issue.number} launch returned no agent id:\n{json.dumps(response, indent=2)[:8000]}",
            error=True,
        )
        return 1

    log(f"Issue #{issue.number} -> agent {agent_id}")
    if agent_url:
        log(f"  URL: {agent_url}")
    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    if run.get("id"):
        log(f"  Run: {run.get('id')} ({run.get('status') or 'unknown status'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
