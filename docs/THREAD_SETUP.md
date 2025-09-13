# Thread Provider Setup

This guide describes configuring OAuth Tester with a Threads OAuth 2.0 application (or an OIDC app if your provider supports discovery).

## Prerequisites
- OAuth Tester running at `https://localhost:8000`
- Local TLS certs generated via `make certs` and trusted in your OS

## Thread App Configuration
1) Create a new OIDC application in Thread.
2) Set allowed/callback URLs:
   - Redirect URI: `https://localhost:8000/auth/callback`
   - Post-logout redirect (optional): `https://localhost:8000/`
3) Enable Authorization Code flow and PKCE (S256).
4) Scopes: `openid profile email` (adjust per your needs).
5) Obtain `client_id` (and `client_secret` if applicable).
6) If your provider supports OIDC discovery, use it. For Threads (Meta), use OAuth 2.0 endpoints from the official docs.

## OAuth Tester .env
Set these variables in `.env`:

```
OAUTH_TESTER_OAUTH__BASE_URL=https://localhost:8000
OAUTH_TESTER_OAUTH__REDIRECT_PATH=/auth/callback
OAUTH_TESTER_OAUTH__CLIENT_ID=...
OAUTH_TESTER_OAUTH__CLIENT_SECRET=...
OAUTH_TESTER_OAUTH__SCOPES=openid profile email
# If provider supports OIDC discovery:
# OAUTH_TESTER_OAUTH__OIDC_DISCOVERY_URL=https://<issuer>/.well-known/openid-configuration

## Threads OAuth 2.0 (no OIDC)
# Per docs/thread_auth.md
OAUTH_TESTER_OAUTH__AUTHORIZE_URL=https://threads.net/oauth/authorize
OAUTH_TESTER_OAUTH__TOKEN_URL=https://graph.threads.net/oauth/access_token
# Optional if a userinfo endpoint is available
# OAUTH_TESTER_OAUTH__USERINFO_ENDPOINT=https://graph.threads.net/me
# OAUTH_TESTER_OAUTH__USERINFO_FIELDS=id,username
OAUTH_TESTER_OAUTH__USE_PKCE=false
# Only enable if your provider requires appsecret_proof semantics for API calls
# OAUTH_TESTER_OAUTH__COMPUTE_APPSECRET_PROOF=true

OAUTH_TESTER_OAUTH__SSL_CERTFILE=certs/localhost.crt
OAUTH_TESTER_OAUTH__SSL_KEYFILE=certs/localhost.key
```

## Run
```
make run
```

Open `https://localhost:8000`, click Login, complete the flow, and view the access token. If configured with a userinfo endpoint, the tester will also display a basic user profile.

Notes
- Use the scope(s) required by Threads; for example, `threads_basic` (confirm against your app’s configuration).
- PKCE: Threads docs do not mention PKCE; we default it to false. You can enable with `OAUTH_TESTER_OAUTH__USE_PKCE=true` if supported.
- appsecret_proof: Not documented for Threads; keep disabled unless explicitly required.

## Trusted Local HTTPS (fix “Not Secure”)

Browsers warn on self-signed certs. Use one of these approaches:

- Recommended (mkcert):
  - Install mkcert (see https://github.com/FiloSottile/mkcert)
  - Generate trusted certs: `make certs-mkcert`
  - Ensure `.env` points to `certs/localhost.crt` and `certs/localhost.key`

- Trust the OpenSSL cert (manual):
  - macOS: open `certs/localhost.crt` in Keychain Access → set “Always Trust”
  - Windows: import into “Trusted Root Certification Authorities”
  - Linux: system-specific; for Chrome-based, you can import in System/Browser cert store; for Firefox (NSS): `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n localhost -i certs/localhost.crt`

After trusting the cert, reload `https://localhost:8000` and the warning should disappear.
