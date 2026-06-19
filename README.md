# wedding
wedding invite

## Landing page password protection (Staticrypt)

The live landing page served at `/index.html` is encrypted.

Edit **index.source.html** locally (this file is gitignored).

Build encrypted landing page:

**PowerShell:**

```powershell
npm install
npm run salt
Password set via STATICRYPT_PASSWORD environment variable — do not commit.
npm run encrypt
```

**Cmd:**

```cmd
npm install
npm run salt
Password set via STATICRYPT_PASSWORD environment variable — do not commit.
```

Note: Staticrypt v3 uses WebCrypto and requires HTTPS or localhost, which GitHub Pages provides.
