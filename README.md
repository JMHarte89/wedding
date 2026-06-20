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

### Notes

- Codes are matched **case-insensitively** — `JHARTE`, `jharte`, and `JHarte`
  all open the same invitation.
- The login placeholder shows a deliberately fake example (`BSanderson`) so no
  real guest's code is suggested.
