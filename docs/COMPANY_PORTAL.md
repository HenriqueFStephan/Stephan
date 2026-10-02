# Company portal

`/empresa` is the page a hiring organization uses to see group results from the HSE-IT forms. It is linked from the footer, not from the public header. While `BLOCKWALL_KEY` is set, the maintenance wall still sits in front of it, like the rest of the site.

The page speaks Portuguese by default, with the same EN toggle as the rest of the site.

## Accounts

Two accounts are seeded in PostgreSQL. Each one is a company. Invitations and answers for one are not visible to the other, and a future company is another row, not a share of these two.

| Username | Password | Company slug | Name on the page |
|---|---|---|---|
| `admin` | `admintest` | `internal` | Uso interno |
| `artigo` | `voltarassamambanhas` | `hse-it` | HSE-IT |

`admin` is for tests on this project. `artigo` is for the paper. Do not upload a client’s list into either of them.

`POST /api/v1/company/login` checks the pair on the server. A match returns a `passage` plus the company slug and name. The passage is not the password. The browser keeps it in `sessionStorage` under `stephan-company-passage` and sends it as `X-Company-Token`. Closing the tab drops the session. Log out drops it too.

The charts on the page are still the simulated wave. The company name above them is the account that signed in.

## What the test data is

`backend/app/services/company_demo.py` builds one wave and caches it.

- 100 anonymous forms. No names, and the overview JSON does not include individual answers.
- The questionnaire is the HSE-IT, 35 items, same order and reverse flags as `frontend/src/app/features/tool/hse-it.ts`.
- Answers are favourable scores from 1 to 5. A higher score is the more favourable condition. Reverse-worded items are reversed before any mean or alpha is calculated.
- Seed `20260928`, so the wave does not change between requests.
- Dates run from 3 August 2026 through 26 September 2026. The newest form in this seed falls on 26 September 2026.
- Four areas, fixed sizes: Operação 34, Administrativo 28, Comercial 22, Cuidado 16.

Each person is drawn from a shared factor, a factor for each of the seven scales, an area shift, and a little item noise. The factors are there so items on the same scale move together. Fully random answers would make Cronbach’s alpha meaningless. The area shifts are there so the four blocks on the page are not copies of each other.

`source` on the overview is `simulated`. The page shows a demonstration note while that is true.

## What the page shows

All of these are group figures. None of them is an individual report or a risk inventory.

1. **Cronbach’s alpha** (required). The large figure is the alpha of all 35 scored items. The table repeats it for each of the seven scales, with the item count, the group mean, and a conventional reading of the coefficient. The line under the title states how many complete responses went into the calculation and the date of the newest one. In this test wave that is all 100 forms, latest 26 September 2026.
2. **Conditions by factor.** Group mean on each scale, from 1 to 5, with the HSE reference marks (20th, 50th, and 80th percentiles) on the bar. Same cuts as the public `/tool` page.
3. **Where the group sits.** How many of the 100 people fall below p20, between p20 and p50, between p50 and p80, and at or above p80, scale by scale.
4. **By area.** The same means split by the four simulated areas.
5. **Responses across the weeks.** How many forms were submitted in each week of the wave.

The reference bands come from the HSE Management Standards Analysis Tool (136 organisations). They describe a position against that benchmark. They are not a diagnosis.

### Cronbach’s alpha in this test

Alpha is calculated in `cronbach_alpha` on the scored items:

```
alpha = (k / (k - 1)) * (1 - (sum of item variances) / (variance of the total score))
```

`k` is the number of items. Variances are sample variances (divisor `n - 1`). Alpha is omitted when fewer than two people or two items are present, or when the total score does not vary.

The reading labels use conventional cut points, not a risk scale: 0.90 and above, 0.80, 0.70, 0.60, and below 0.60.

“Latest data” means every complete form in the current wave, and the date shown is the newest `submitted` day in that set. It is not a rolling window and it is not one person’s form.

## Plan for real data

Keep `CompanyOverview` as the response the page already renders. When a real campaign replaces the fixture, `demo_overview()` becomes a query and the template stays.

1. **Accounts.** `admin` and `artigo` are stored users, each tied to one company. A future company is a new `companies` row, an open round, and a `company_users` row. Do not point that company at `internal` or `hse-it`. Passwords are hashed. The passage is issued on the server. The password is not compiled into the Angular app.
2. **Ingest.** The campaign store, the invitation list, and the anonymity rules are in `docs/TOOL.md`. This page uploads the email list for the signed-in company and shows the round as two percentages, finished and not yet. It does not list who finished. The simulated overview stays until real answers replace it. A link with `?t=` opens the campaign form and stores one anonymous answer for that company.
3. **Rows.** Anonymous answers are `hse_responses` in that document: company, round, day, a JSON object for demographics that is not frozen yet, and 35 raw marks. No email, token, or invitation id on the answer.
4. **Overview.** Filter those rows to the logged-in company and to the open campaign (or an explicit date window). Return the same JSON. Set `source` to `recorded`. The demonstration note then hides.
5. **Alpha.** Call the same `cronbach_alpha` on the scored items of that set every time the overview is read. Keep showing `n` and the newest `submitted_on`. Decide in the campaign whether “latest” means the open wave or a trailing window, and say that choice in the sentence that already carries `n` and the date.
6. **Small groups.** Do not return an area, or any other split, with fewer than 5 people. Do not open the company view under a minimum you agree with the client (10 is a sound starting point). The demo does not apply this rule: the smallest area has 16 people.
7. **Privacy.** This page stays aggregate. Do not add a person list, a raw export, or a single-form view here. The public copy on `/tool` already says one answer is not a group result; the company page should keep that distinction.

Until real answers replace the simulated wave, the numbers on `/empresa` are still the seeded wave above. The invitation list is a separate store. See `docs/TOOL.md`.
