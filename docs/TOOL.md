# HSE campaign (`/tool`)

This is the store for one company’s HSE Management Standards Indicator Tool wave: about 300 anonymous answers, plus the invitation list used to send each person a link. It replaces nothing on the public site. A public-site schema (pages, posts, comments, practice contact details) was drafted elsewhere and has been discarded. Do not rebuild it.

`/tool` shows the introduction, then the sociodemographic questionnaire (Anexo B), then the 35 items. With `?t=`, that is the campaign form. Without a token, it is the local reading and posts nothing. The working Portuguese for the 35 items lives in `frontend/src/app/features/tool/hse-it.ts` and is not copied into the database. Anexo B sentences live in `frontend/src/app/features/tool/profile.ts`. The database stores codes.

## Where PostgreSQL runs

The API already runs on the existing Lightsail instance in São Paulo (`docs/workflows/deploy-lightsail.md`). The campaign database is PostgreSQL on that same machine. It listens on `127.0.0.1` only. The API is the only process that connects.

A Lightsail managed database is a different product (from about $15 a month) and is out of scope. Do not create one. `scripts/postgres_on_lightsail.sh` installs packages on the instance that is already paid for. If a screen asks for a new database product or a card, stop.

Local work uses the same engine, published only to `127.0.0.1:5432`. See [Local setup](#local-setup).

## Connection string

`DATABASE_URL` lives with the other secrets:

- locally, repo-root `debt.txt` (gitignored)
- on the server, `/opt/stephan/debt.txt`, which deploy does not replace

`debt.txt.example` names the key and leaves it empty. The local Docker password `stephan` is a development default in `docker-compose.yml`. It is not the Lightsail password. The server script generates that password on the machine and writes the URL into `debt.txt` without printing it.

The API refuses a URL whose host is not `127.0.0.1`, `localhost`, `::1`, or the Compose name `db`. A managed-database hostname will not connect.

An empty `DATABASE_URL`, or any non-PostgreSQL value, leaves the rest of the site up. The company overview stays the simulated wave. The invitation list returns “database unavailable” until PostgreSQL is running.

## Companies

Two companies are seeded. A later company is another row. It does not share rounds, uploads, invitations, or answers with these two.

| Slug | Name | Account |
|---|---|---|
| `internal` | Uso interno | `admin` / `admintest` |
| `hse-it` | HSE-IT | `artigo` / `voltarassamambanhas` |

Each has an open round `rodada-1`. `internal` is for tests on this project. `hse-it` is for the paper. Do not upload a client list into either.

`/empresa` stays in the footer. `/tool` stays out of the header and the footer.

## Rounds

Invitations belong to a company and to one open round. A company can have only one round with `closed_on` empty. Uploads in this step attach to that round. “Already invited” means the email is already in this round, not that it can never be invited again. Opening another round later is a new row with `closed_on` set on the previous one. There is no screen for that yet.

## Two tables that must not meet

```
companies
   └── company_rounds
          ├── invitation_uploads     (the file the admin sent)
          │      └── invitations     email, link token, pending|submitted
          └── hse_responses          anonymous answers and demographics
```

There is no foreign key from `hse_responses` to `invitations`.

The email exists so we can send the link and see who has not finished. It lives only on `invitations`. The answer row does not store:

- the email
- the link token
- the invitation id
- an IP address, or any other client address

`company_id` and `round_id` are on both sides because every answer in the wave belongs to that company and that round. They are not a person. Hundreds of rows share them.

Marking an invitation `submitted` is what blocks a second response. The future form must do that in the same transaction as the insert, without copying the invitation id onto the answer:

1. Look up the invitation by `link_token_hash` where `status = 'pending'`.
2. Insert `hse_responses` with a new random id.
3. Set the invitation to `submitted` and set `submitted_at`.
4. If the invitation was not pending, roll the insert back.

`submitted_on` on the answer is a date. `submitted_at` on the invitation is a timestamp. They are not the same column copied across. With a quiet day and one submission, the day can still line up with the person who finished. That is a limit of “who has finished”, not a join key to add. Do not store a shared id to make that match easier.

The link token stays on the invitation so the same link keeps working after the message is sent. `sent_at` records that the message left. The upload response does not return tokens. `link_token_hash` is the lookup key for the later form. Neither value is written on the answer.

The original file is not kept. A rejected file is not stored at all.

## Anexo B on the form

The sociodemographic and occupational questions are the page after the introduction, before the 35 items. They belong to the form. Each answer is a column on `hse_responses`, the same row as `i01`–`i35`. They are not columns on `invitations`. There is still no foreign key from an answer to an invitation.

Age band and economic sector are required. The other nine may be left blank. A blank is SQL `NULL`. A new form that omits a required answer is refused, and the invitation stays `pending`.

Stored values are stable codes, not the sentences on the page. A name, a job title, or any other free text cannot be written into these columns.

`demographics` is that same set of codes as a JSON object, written in the same insert as the columns. It is not an open bag. Unknown keys are refused. Keys and codes are lowercase.

| Column | Required | Codes |
|---|---|---|
| `age_band` | yes | `18_24`, `25_34`, `35_44`, `45_54`, `55_64`, `65_plus` |
| `gender` | no | `female`, `male`, `undisclosed` |
| `education` | no | `fundamental`, `high_school`, `higher_incomplete`, `higher_complete`, `postgraduate` |
| `economic_sector` | yes | `manufacturing`, `retail`, `services`, `health`, `education`, `it`, `construction`, `transport`, `agribusiness`, `public_admin`, `other` |
| `org_size` | no | `micro`, `small`, `medium`, `large`, `unknown` |
| `employment_bond` | no | `clt`, `public_statute`, `autonomous_pj`, `intern_apprentice`, `other` |
| `tenure_org` | no | `lt_1`, `y1_3`, `y4_10`, `gt_10` |
| `tenure_profession` | no | `lt_1`, `y1_5`, `y6_15`, `gt_15` |
| `work_shift` | no | `day_fixed`, `night_fixed`, `rotating`, `flexible` |
| `leadership` | no | `yes`, `no` |
| `region` | no | `north`, `northeast`, `center_west`, `southeast`, `south` |

These keys are still refused, on top of any key that is not in the table above:

`name`, `nome`, `full_name`, `email`, `e-mail`, `mail`, `job`, `job_title`, `jobtitle`, `cargo`, `funcao`, `função`, `token`, `link_token`, `ip`, `invitation_id`, `invitation`

Do not add name or job title unless that is decided later, in writing, as its own change.

## Re-identification inside one company

About 300 people is still a small workplace. Age band together with gender, sector, region, or leadership can point at one person even when the row has no name. The company page must stay an aggregate. Do not add a person list of answers, a raw export, or a single-form view. The invitation list (who has not finished) is a separate list and must not be shown beside an answer.

The same warning is already in `docs/COMPANY_PORTAL.md` for groups under five. It applies to demographics here even when the whole company is large enough to show a mean.

## The instrument

HSE Management Standards Indicator Tool, 35 items, the last six months, official order. The database columns `i01`–`i35` are items 1–35 in that order, not grouped by area. Each value is the raw mark from 1 to 5. Reverse scoring is applied when a mean is calculated, not when the row is stored. Favourable score for a reverse item is `6 - raw`.

Items 1–23 use the frequency scale: 1 never, 2 seldom, 3 sometimes, 4 often, 5 always.

Items 24–35 use the agreement scale: 1 strongly disagree, 2 disagree, 3 neutral, 4 agree, 5 strongly agree.

| Area | Items | n | Reverse |
|---|---|---|---|
| Demands | 3, 6, 9, 12, 16, 18, 20, 22 | 8 | all of them |
| Control | 2, 10, 15, 19, 25, 30 | 6 | none |
| Managerial support | 8, 23, 29, 33, 35 | 5 | none |
| Peer support | 7, 24, 27, 31 | 4 | none |
| Role | 1, 4, 11, 13, 17 | 5 | none |
| Relationships | 5, 14, 21, 34 | 4 | all of them |
| Change | 26, 28, 32 | 3 | none |

Reverse item numbers: 3, 5, 6, 9, 12, 14, 16, 18, 20, 21, 22, 34.

The working translation already in `frontend/src/app/features/tool/hse-it.ts` is for the local reading. It is not the confirmed Portuguese instrument. Do not copy those sentences into the database, into a second module, or onto the campaign form until the wording is confirmed.

## Access

Each person gets one link:

`https://stephan.net.br/tool?t=<link_token>`

The host is `PUBLIC_APP_URL` (default `https://stephan.net.br`), not `FRONTEND_URL`. A local API still sends the public site.

`POST /api/v1/tool/access` with the token opens the form when the invitation is `pending`. `POST /api/v1/tool/responses` stores the 35 raw marks on that invitation’s company and round, then marks the invitation `submitted`, in one transaction. The token is not written on the answer. A second post with the same token is refused. No token: `/tool` stays the local reading and posts nothing. `/tool` is not in the header or the footer. Do not link the local reading.

Saving the list sends the link to each new address. The message uses the site colors and the Stephan lockup: a short note, a button, and the same link in plain text. It does not name the person. SMTP settings (`SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`) live in `debt.txt`. If they are missing, a new address is not stored. An address already invited in this round does not get a second message.

## Admin upload

On `/empresa`, after login, “Quem recebe o link” accepts one file. The API is `POST /api/v1/company/invitations` with the company session header and a multipart field named `file`. `GET /api/v1/company/invitations` returns the round label, how many people were invited, and the shares who have finished and who have not. It does not return emails, tokens, or answers. The company page shows those shares as percentages.

Rules for every format:

- The only field is `email`. A name column is rejected. Any other column is rejected. Nothing from a rejected file is stored.
- Empty rows are ignored.
- The same email twice in the file: the first is kept, the later ones are reported under `duplicates_in_file` and do not get a second link.
- An email already invited in this round is reported under `already_invited` and does not get a second link.
- Addresses are matched case-insensitively and stored in the normalized form.
- UTF-8. A CSV that is not UTF-8 is rejected.
- At most 1 MB and 5 000 data rows. The wave is about 300 people.
- Other worksheets in an Excel file are not read and are not stored.

The JSON shape is one object, not a list of accepted variants:

```json
{
  "invitations": [
    { "email": "pessoa.um@example.com" },
    { "email": "pessoa.dois@example.com" }
  ]
}
```

Example: [`docs/tool/invitations.json`](tool/invitations.json).

A bare array, a second root key, or a second key on an invitation (including `name`) is rejected.

CSV: header cell exactly `email`, comma-separated.

```csv
email
pessoa.um@example.com
pessoa.dois@example.com
```

Example: [`docs/tool/invitations.csv`](tool/invitations.csv).

Brazilian Excel often uses a semicolon. If the header line contains `;` and the header cell is exactly `email`, the separator is a semicolon. A trailing semicolon on a one-column file is empty and is ignored. A second header such as `nome` is rejected.

```csv
email;
pessoa.tres@example.com;
```

Example: [`docs/tool/invitations.semicolon.csv`](tool/invitations.semicolon.csv).

Excel: the first worksheet of an `.xlsx` file. Row 1 is the header `email`. Same column rule as CSV.

Example: [`docs/tool/invitations.xlsx`](tool/invitations.xlsx).

A successful response looks like this. Tokens are not included.

```json
{
  "round_label": "rodada-1",
  "accepted": 2,
  "ignored_empty": 0,
  "duplicates_in_file": [],
  "already_invited": [],
  "invalid": []
}
```

## Tables

`companies`

| Column | |
|---|---|
| `id` | uuid |
| `slug` | unique. `internal` and `hse-it` are seeded |
| `name` | display name, not frozen |
| `created_at` | |

`company_rounds`

| Column | |
|---|---|
| `id` | uuid |
| `company_id` | |
| `label` | unique per company, `rodada-1` today |
| `opened_on` | date |
| `closed_on` | null while the round accepts uploads |

`invitation_uploads`

| Column | |
|---|---|
| `id` | uuid |
| `company_id`, `round_id` | |
| `source_name` | file name only, not a person |
| `format` | `json`, `csv`, or `xlsx` |
| `created_at` | |

`invitations`

| Column | |
|---|---|
| `id` | uuid, not copied onto an answer |
| `company_id`, `round_id`, `upload_id` | |
| `email` | normalized |
| `link_token` | secret in the link that was sent |
| `link_token_hash` | unique, lookup for the later form |
| `status` | `pending` or `submitted` |
| `submitted_at` | set only when status is `submitted` |
| `sent_at` | when the message left, empty if it never did |
| `created_at` | |

Unique on `(round_id, email)`.

`hse_responses`

| Column | |
|---|---|
| `id` | new random uuid |
| `company_id`, `round_id` | the wave, not a person |
| `submitted_on` | date |
| `demographics` | the same Anexo B codes as JSON, default `{}` on older rows |
| `age_band` … `region` | Anexo B codes, null when that question was skipped |
| `i01` … `i35` | raw marks 1–5, official order |

Schema file: `backend/app/db/schema.sql`. The API applies it on the first invitation request.

`record_response` in `backend/app/services/campaign_store.py` inserts an answer with no email, token, or invitation id. `POST /api/v1/tool/responses` calls it and then marks the invitation submitted, in one transaction.

## Local setup

PostgreSQL 16 in Docker, bound to localhost, same database name and role the server script creates.

```powershell
docker compose up -d db
```

That publishes `127.0.0.1:5432` only. User `stephan`, password `stephan`, database `stephan`. This password is for the laptop. Do not copy it to Lightsail.

If Docker is not installed, the same listener can be started without a Windows service:

```powershell
python scripts/postgres_local.py
```

That uses local PostgreSQL binaries, keeps the data in `%LOCALAPPDATA%\Stephan\postgres`, and binds `127.0.0.1:5432` only.

In `debt.txt`:

```
DATABASE_URL=postgresql://stephan:stephan@127.0.0.1:5432/stephan
```

Restart the API after changing `debt.txt`. The first upload creates the tables and the seeded companies.

If the API itself runs under Compose, its URL is `postgresql://stephan:stephan@db:5432/stephan` (the Compose network, still not a public port). Host-run `uvicorn` uses `127.0.0.1`.

`docker compose up` also starts the API and the site. For day-to-day work, `docker compose up -d db` plus the usual `uvicorn` and `npm start` is enough.

Check:

```powershell
docker compose ps
```

The `db` service should be healthy, and `ss` or the Docker port list should show `127.0.0.1:5432`, not `0.0.0.0:5432`.

## Lightsail

On the instance, as root, if you need to run it by hand:

```bash
sudo bash postgres_on_lightsail.sh
```

The script is in the repo at `scripts/postgres_on_lightsail.sh`. A push to `main` runs it on the instance before the API restarts. It:

- installs PostgreSQL from the Ubuntu packages already available on the instance
- sets `listen_addresses = 'localhost'`
- stops if `pg_hba.conf` allows `0.0.0.0/0` or `::/0`
- checks that port 5432 is loopback only
- creates role and database `stephan` if needed
- writes `DATABASE_URL` into `/opt/stephan/debt.txt` when that key is missing
- restarts `stephan-api` if the unit exists

It does not open a security-group port and it does not call the Lightsail database API.

After the first invitation request, the tables exist. Confirm from the server, not from your laptop:

```bash
sudo -u postgres psql -d stephan -c "\dt"
ss -ltn 'sport = :5432'
```

## What a later step still has to do

- Confirm the Portuguese HSE item wording. The working translation is already on the form.
- Render `/tool` only when `t` matches a pending invitation. No token, no page.
- Save the 35 raw marks and Anexo B in one transaction with the status change above. This is what `POST /api/v1/tool/responses` does.
- Replace `admin` / `admintest` before a real list is uploaded on the server.
- Point the company overview at `hse_responses` when a real wave should replace the simulated one. Until then, `source` stays `simulated`.
