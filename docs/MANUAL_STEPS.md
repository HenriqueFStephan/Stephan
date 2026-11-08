# Manual steps

Checklist of work that stays outside the code. Do these when you are ready. Leave a box unchecked until that step is done. New features append a section here.

The server does not pick up this file, the backup script, or the WhatsApp list until a push to `main` deploys. `/opt/stephan/debt.txt` is not replaced by that deploy.

## Before the first company uses the form

- [ ] Turn on Lightsail automatic snapshots for the São Paulo instance that serves `stephan.net.br`. In the Lightsail console, open that instance, then Snapshots, and enable the daily automatic snapshots (keep 7). Turning them on does not create a new database. Storage is about $0.05 per GB-month. If a screen asks you to create a database or to enter a card for a database product, stop.
- [ ] Create one manual snapshot of that same instance and keep it until the first company has uploaded a list and a backup has landed in `/var/backups/stephan`.
- [ ] Choose the mailbox that should receive contact messages and order notices. Set `CONSULTING_NOTIFY_TO` to that address in the repo-root `debt.txt`, and set the same key in `/opt/stephan/debt.txt` on the server. Then restart the API: `sudo systemctl restart stephan-api`. Contact messages include the full text. An order notice includes the reference, the company name, and the plan.
- [ ] Commit and push to `main` when you want the server to run the backup and the list changes. The deploy backs up the current database first, then updates the app. Until that push, production still has the previous invitation behavior.

## WhatsApp for the form link

The number that sends is **+55 19 99877-2525**. The company does not choose a channel. A phone number in the list is sent on WhatsApp. An email is sent by email. One file can contain both.

- [ ] In Meta Business Suite, open WhatsApp Manager and use the WhatsApp Business Platform (Cloud API). This is not WhatsApp Web and not a session of the phone app.
- [ ] Register **+55 19 99877-2525** as the business number. That SIM cannot stay logged in to the regular WhatsApp app at the same time. Meta sends a code to it by text or call.
- [ ] Copy the **Phone number ID** from the API setup. It is a long numeric id. It is not +55 19 99877-2525.
- [ ] Create a permanent access token (a system user in Business Settings, with `whatsapp_business_messaging`). A token from the API explorer expires in about a day. Do not put this token in the Angular app.
- [ ] Create a message template and wait until Meta marks it **Approved**.
  - Name: `stephan_questionario`
  - Language: Portuguese (BR) — `pt_BR`
  - Category: Utility
  - Body, with a single variable. The variable has text before it and text after it:

```
Este é o seu link para o questionário das condições de trabalho.

{{1}}

O link é só seu. Não o reencaminhe.
```

  - Sample value for `{{1}}`: `https://stephan.net.br/tool?t=exemplo`
- [ ] Put these two lines in the repo-root `debt.txt` and in `/opt/stephan/debt.txt` on the server:

```
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

- [ ] Restart the API (`sudo systemctl restart stephan-api`), or push to `main` if this code is not on the server yet.

Until those two keys are set, a file that contains only phone numbers is refused and nothing from it is stored. A file that also contains emails still sends the emails, and the phones are listed on the company page as not stored.

Until the template is approved, a phone number is kept and the same link is tried again. It shows with the other addresses whose message has not left.
