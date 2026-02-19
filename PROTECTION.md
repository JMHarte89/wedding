# Password protection

## test/ — localStorage gate (bypassable)

The **test/** area uses a client-side gate: `test/auth.js` redirects to `test/login.html` when `localStorage.getItem('wedding_role')` is missing. The phrase is checked in `test/login.html` and stored in localStorage.

**Bypass:** Anyone can set `wedding_role` in DevTools (e.g. `localStorage.setItem('wedding_role','guest')`) and reload or open test URLs directly. The HTML is served in plaintext; the “protection” is only a redirect. Do not rely on it for real access control.

## Root — Staticrypt (non-bypassable)

The **root landing page** (`/index.html`) is encrypted with [Staticrypt](https://github.com/robinmoisson/staticrypt). The file served at the root is ciphertext; the browser prompts for the passphrase and decrypts in-browser with WebCrypto. Direct navigation to `/index.html` does **not** reveal the content without the correct passphrase.

- **Source of truth (local only):** `index.source.html` — gitignored; edit this and run `npm run encrypt` to regenerate `index.html`.
- **Served file:** `index.html` — encrypted; commit this. No plaintext landing HTML is committed.

## Git history warning

If the repo was **public** and previously contained plaintext `index.html`, that plaintext may still be visible in **git history** (e.g. via `git show <old-commit>:index.html`). To remove it you would need to rewrite history (e.g. `git filter-branch` / BFG) or move to a fresh repo and force-push. This doc does not change existing history.
