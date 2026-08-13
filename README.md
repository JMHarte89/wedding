# wedding
wedding invite

## Guest list — source of truth

**`data/guestlist.csv` is the SINGLE SOURCE OF TRUTH for the guest list.**
Edit this file to add, remove, or change guests.

### Columns

| Column | Meaning |
| --- | --- |
| `code` | Login code, first initial + surname (e.g. `JHarte`). **Must be unique.** Used at the gate; matched **case-insensitively**. |
| `greeting` | How the letter addresses the household — the page shows `Dear [greeting],` (e.g. `Jase, Becki, Robin & Archie`). Quote it if it contains commas. |
| `members` | Everyone in the household, **pipe-separated** (e.g. `Jase Harte\|Becki Harte\|Robin (3)`). |
| `day` | `TRUE`/`FALSE` — invited to the full day. |
| `evening` | `TRUE`/`FALSE` — invited to the evening. |
| `notes` | Free-text notes (e.g. "surname TBC"). |
| `confirm` | *(optional)* A friendly yes/no question shown before the invitation opens, for similarly-named households (e.g. two Robert Blackshaws): "Just checking — are you married to Carole?". Leave blank for everyone else. |
| `confirmElse` | *(optional)* Hint shown if they answer "No" to `confirm` (e.g. "If you're Robert married to Marie, your code is RBlackshaw."). Optional even when `confirm` is set. |
| `aliases` | *(optional)* Extra login codes that also open this invitation, pipe-separated (e.g. `TBennett` so either partner's initial works). Must be unique like `code`. |
| `label` | *(optional)* Free-text tag for your own admin use; not shown on the site. |
| `table` | *(optional)* The household's table, by tree name (`Oak`, `Maple`, `Willow`, `Elm`, `Ash`, `Magnolia`, `Acer`, `Rowan`, `Holly`, or `Top Table`). Shown on their place card once they unseal, and highlighted on the table plan. Leave blank for anyone with no seat (evening-only guests). |
| `access` | *(optional)* `couple` for Jase & Becki. See "Who sees what" below. |

### Regenerating the site data

The website reads `data/guests.json`, which is **auto-generated** — do **NOT**
edit `guests.json` by hand.

After editing the CSV, run:

```bash
node scripts/build-guests.js
```

This regenerates `data/guests.json` from `data/guestlist.csv`. The script
warns if any two codes collide (case-insensitively).

Then commit **both** `guestlist.csv` and `guests.json` and push.

### Who sees what

Every guest sees their own table on a place card behind the letter, and their
table highlighted on the room plan in the **Your Table** section.

Anyone on the **Top Table** — the wedding party — additionally sees the
`.top-table-only` sections: the **full seating plan** (every table and who is
on it) and the **order of service**. That's driven by `table` being
`Top Table`, or by `access` being `couple`; no separate flag to maintain.

This is a soft gate only. `data/guests.json` is publicly readable, so the
extra sections are hidden from ordinary guests, not protected from them.

The full seating plan is **generated at runtime** from `guests.json` by
`js/wedding.js` — it can't drift out of step with the place cards. The private
`data/seating-plan.xlsx` is the working document for planning; it is
git-ignored and never published.

### Notes

- Codes are matched **case-insensitively** — `JHARTE`, `jharte`, and `JHarte`
  all open the same invitation.
- The login placeholder shows a deliberately fake example (`BSanderson`) so no
  real guest's code is suggested.
