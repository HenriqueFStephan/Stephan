# NFS-e nacional

The charge needs a Nota Fiscal de Serviço eletrônica that a buyer can check on the national portal. This page is the map. It is not a lawyer's or an accountant's opinion, and it does not turn the site into an issuer.

The sample XML and the consultation screenshot were used only for the field names and the codes. Names, CPF, CNPJ, addresses, e-mails, and the access key from that sample stay out of the repo.

## Two different doors

| Door | What it does | Address |
|------|----------------|---------|
| Consulta Pública | Checks a note that already exists. The screenshot is this door. It asks for the 50-digit access key, or for the issuer's CPF/CNPJ, the DPS series, the DPS number, and the city. | `https://www.nfse.gov.br/consultapublica` |
| Emissor Nacional | Creates the note, after the city has turned the public issuers on and the taxpayer is authorized. Login is the digital certificate (e-CNPJ) or gov.br. | Portal da NFS-e, `https://www.gov.br/nfse` |
| Technical layout | The XML namespace `http://www.sped.fazenda.gov.br/nfse`, version `1.01`. | `https://www.sped.fazenda.gov.br` and the library at `https://www.gov.br/nfse` |

Emitting and checking are not the same screen. A note appears on the consultation portal only after some issuer has authorized it and shared it with the Ambiente de Dados Nacional (ADN).

The sample was not born in the Emissor Nacional Web. Official reading of its flags:

- `ambGer` `1` means the city's own system. `2` would mean the Emissor Nacional.
- `tpEmis` `2` means the city wrote the note in its own layout and transcribed it into the national layout. `1` means it was already in the national layout.
- `serie` `10001` sits in the API range `00001`–`49999`. The national website uses `70000`–`79999`. The phone app uses `50000`–`69999`. Manual transcription uses `80000`–`89999`.

So "we have to emit in the national system" can mean two workable paths. The accountant picks one:

1. The city uses the Emissor Nacional. Someone with the practice's e-CNPJ issues the note there. The consultation portal then finds it with `ambGer` `2`.
2. The city keeps its own issuer, and the city shares the note with the ADN. The consultation portal still finds it, with `ambGer` `1`, as in the sample.

The Angular app does not emit. A certificate and a gateway token never go in the frontend or in git. They belong in `debt.txt` and on Render, and only after an issuer is actually connected. Until then the payment button records the order and does not charge.

## What the XML is

The file has two documents nested together.

The inner `DPS` (Declaração de Prestação de Serviços) is what the issuer sends: who provided the service, who hired it, what the service was, and the price. The outer `NFSe` is what the system returns after it accepts that declaration: the note number, the city names, the tax descriptions, and the access key.

`Id` on `infNFSe` is `NFS` plus the 50-digit access key. The consultation portal asks for the 50 digits, without the `NFS` prefix. Official composition: city code (7) + environment (1) + federal-id type (1) + federal id (14) + note number (13) + year and month (4) + random code (9) + check digit (1).

`nDPS` is the issuer's own declaration number. `nNFSe` is the national note number, 13 digits, assigned when the declaration becomes a note. `nDFSe` exists on a transcribed note (`tpEmis` `2`) and is the number from the city's own system. Bookkeeping uses `nNFSe` and the access key, not the DPS series.

## Tags in the sample

Values below are the codes in the sample, not a decision that this practice uses them. The issuer and the buyer in that file are a sample.

| Tag | Sample | Meaning |
|-----|--------|---------|
| `versao` | `1.01` | Layout version. |
| `xLocEmi` | city name | City that issued the note. The system fills the name. |
| `xLocPrestacao` | city name | City where the service was provided. |
| `nNFSe` | a note number | National note number. |
| `cLocIncid` | 7-digit IBGE | City where the ISS is due. |
| `xLocIncid` | city name | Name of that city. |
| `xTribNac` | `Psicologia.` | Official name of the national service code. |
| `xTribMun` | a municipal name | Official name of the city's own service code. |
| `xNBS` | `Serviços de psicologia` | Official name of the NBS code. |
| `verAplic` | `1.01` | Version of the program that built the file. |
| `ambGer` | `1` | `1` city system, `2` Emissor Nacional. |
| `tpEmis` | `2` | `1` already national, `2` transcribed from the city's layout. |
| `cStat` | `100` | Ordinary generated note. The national FAQ uses `102` for an administrative or judicial exception, which this is not. |
| `dhProc` | a datetime | When the system processed the note. |
| `nDFSe` | same number as the city note | City number, only meaningful on a transcription. |
| `emit/CNPJ` | the supplier | Supplier's CNPJ. |
| `emit/IM` | municipal registration | Inscrição municipal. Required to issue. |
| `emit/xNome` | legal name | Razão social. |
| `emit/xFant` | trade name | Nome fantasia. |
| `enderNac` | address | Street, number, district, IBGE city code, state, CEP. |
| `emit/email` | an e-mail | Supplier e-mail printed on the note. |
| `valores/vBC` | `0.00` | ISS tax base. Zero here because the Simples regime below does not highlight ISS on the note. |
| `valores/vISSQN` | `0.00` | ISS amount. Zero for the same reason. |
| `valores/vLiq` | the price | Amount the buyer pays. This is the number the payment page has to match. |
| `tpAmb` | `1` | `1` production, `2` homologation. |
| `dhEmi` | a datetime | When the DPS was issued. |
| `serie` | `10001` | DPS series. The range says which channel issued it. See above. |
| `nDPS` | a declaration number | Issuer's sequential number inside that series. |
| `dCompet` | a date | Competence date of the service. |
| `tpEmit` | `1` | Who sent the DPS: `1` provider, `2` buyer, `3` intermediary. |
| `cLocEmi` | 7-digit IBGE | City of emission. |
| `prest/CNPJ` and `prest/IM` | supplier | Same identity as `emit`, on the declaration. |
| `opSimpNac` | `3` | `1` not in Simples, `2` MEI, `3` ME or EPP in Simples. |
| `regApTribSN` | `1` | How Simples is assessed. See the next section. |
| `regEspTrib` | `0` | Municipal special regime. `0` is none. |
| `toma` | the buyer | CPF or CNPJ, name, address, e-mail. A company note uses `CNPJ`, not `CPF`. |
| `cLocPrestacao` | 7-digit IBGE | City where the service was provided. |
| `cTribNac` | `041601` | National service code. Six digits, no dots. See below. |
| `cTribMun` | `001` | The city's own code for that service. It is not universal. Another city uses another number. |
| `xDescServ` | free text | What was sold, in words. This must match the contract. |
| `cNBS` | `123019800` | NBS code, nine digits. See below. |
| `vServ` | the price | Service price before a withholding. |
| `tribISSQN` | `1` | `1` taxable, `2` immunity, `3` export, `4` not levied. |
| `tpRetISSQN` | `1` | `1` not withheld, `2` withheld by the buyer, `3` withheld by an intermediary. |
| `indTotTrib` | `0` | The issuer is not printing an estimated tax total (Decreto 8.264/2014). |

`pAliq` is absent. When the city of incidence is in the national system, the system supplies the ISS rate. The issuer does not invent it.

## The psychology codes

`cTribNac` `041601` is item 04.16 of the list attached to Lei Complementar 116/2003: Psicologia. On the national list it is written `041601`.

`cNBS` `123019800` is NBS `1.2301.98.00`, Serviços de psicologia. The national correlation (Anexo VIII, a first draft, not a frozen rule) links LC 116 item 04.16 to that single NBS. The same annex also points item 04.16 at IBS/CBS operation indicators `030101`, `030102`, and `100301`, and classification `200029`. Those tags are not in this sample. They belong to the consumption-tax reform layout, which is still moving. Do not add them until the accountant says the layout in force requires them.

`cTribMun` `001` with the label "ATIVIDADES DE PSICOLOGIA" is that city's code. It is not a national constant.

That sample describes clinical sessions. This site sells a cycle of organizational psychosocial-risk work, and the payment page says the cycle is not clinical care, not an occupational exam, and not an individual report. Item 04.16 may still be the right code, because the practice is psychology. Item 17.01 of the same law (advice, analysis, research, and supply of information that no other item already covers) is the other candidate the accountant has to rule out. The site must not hard-code `041601` until that choice is made. A wrong code is rejected, or it taxes the note in the wrong city.

The description (`xDescServ`) is where the cycle is named in the buyer's words. A council number can sit in that sentence, the way the sample put a CRP number there. `supplier.councilRegistration` in `offer.config.ts` is the place we already reserved for that number.

## Simples Nacional and Fator R

`opSimpNac` `3` plus `regApTribSN` `1` means a Simples ME/EPP whose federal taxes and whose ISS are both paid inside the Simples (the DAS), not as a separate ISS on the note. That is why `vBC` and `vISSQN` are `0.00` while `vLiq` equals `vServ`. The buyer pays the service price. The tax is the supplier's, settled later on the DAS.

`regApTribSN` has two other values, and they change the note:

| Value | What is inside the DAS | What the note does with ISS |
|-------|------------------------|-----------------------------|
| `1` | Federal taxes and ISS | ISS base stays zero. The sample. |
| `2` | Federal taxes only | ISS is calculated on the note, under the city's rule. |
| `3` | Neither | Federal taxes and ISS are both calculated on the note. |

Fator R is not a tag. It decides which Simples annex applies to this kind of service, under Lei Complementar 123/2006, art. 18, §§ 5º-J and 5º-M. It is the payroll of the last 12 months divided by the gross revenue of the last 12 months. At or above 28%, Anexo III applies, and the nominal rate starts at 6%. Below 28%, Anexo V applies, and the nominal rate starts at 15.5%. The accountant recalculates it every month. It changes what the practice pays on the DAS. It does not, by itself, change the price on the buyer's note.

The payment page today refuses to show a total until `price.issRatePercent` is filled, and then it prints a line such as "ISS 2% incluso". Putting `0` there would print "ISS 0% incluso", which is the wrong sentence for regime `1`. Leave the rate empty until the accountant says which regime this CNPJ uses. If it is regime `1` and nothing is withheld, the page should say that ISS is not highlighted because it is inside the DAS, and the total should be the service price. That sentence is not written yet.

## Withholding, because the buyer here is a company

The sample buyer is a person, and `tpRetISSQN` is `1` (nothing withheld), so the liquid amount equals the price. This site sells to a company. A company buyer can be required to withhold ISS, and sometimes federal taxes. If that happens, `vLiq` is smaller than `vServ`, and the payment page has to charge `vLiq`. The accountant has to say, for a CNPJ buyer of this service, whether anything is withheld.

## What the site already has, and what is still missing

Cadastro already collects the buyer side of `toma`: razão social, CNPJ, invoice e-mail, phone, and the fiscal address. `offer.config.ts` already collects the supplier side of `emit` and `prest`: legal name, CNPJ, inscrição municipal, address, e-mail, phone.

Still absent, and required before anyone can emit:

| Fact | Why | Where it goes once it is real |
|------|-----|-------------------------------|
| IBGE code of the supplier's city, 7 digits | `cLocEmi` and the supplier address | Beside the address in `offer.config.ts` |
| IBGE code of the buyer's city | `toma` / `cMun`. ViaCEP returns it and the form currently drops it | On the signup draft, filled with the CEP lookup |
| Simples status and `regApTribSN` | Decides whether the note highlights ISS | `offer.config.ts`, after the accountant confirms |
| `cTribNac`, `cNBS`, and the city's `cTribMun` | Identifies the service | `offer.config.ts`, after the accountant confirms. Not `041601` by default |
| One sentence that describes this cycle | `xDescServ` | The offer copy, not a new invention per order |
| Whether a company buyer withholds ISS or federal tax | `vLiq` versus `vServ` | The price breakdown on `/pagamento` |
| e-CNPJ and the chosen issuer (Emissor Nacional, the city's system, or an API) | Actually sending the DPS | `debt.txt` and Render. Never the Angular app |

The order file `backend/data/orders.jsonl` already keeps the buyer data a later emission step would read. It is gitignored and it contains the signer's CPF.

## What to ask before changing the page

1. Is this CNPJ Simples ME/EPP, and is `regApTribSN` `1`, `2`, or `3`?
2. For this month, is Fator R at or above 28%? That is a DAS question. It does not go on the buyer's note unless the price itself is being set to cover it.
3. Is this cycle item `04.16` (psicologia, NBS `1.2301.98.00`) or item `17.01` (consultoria, análise e pesquisa), and what is the city's `cTribMun` for that item?
4. When the buyer is a company, is ISS withheld? Are federal taxes withheld? The charged total has to be `vLiq`.
5. Which door emits: Emissor Nacional on `gov.br/nfse`, the city's own system, or an API the accountant already uses?
