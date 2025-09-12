# Thread Provider Setup

This guide describes configuring OAuth Tester with a Thread OIDC application.

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
6) Discovery preferred: capture the OIDC discovery URL; otherwise collect the authorize/token/JWKS endpoints.

## OAuth Tester .env
Set these variables in `.env`:

```
OAUTH_TESTER_OAUTH__BASE_URL=https://localhost:8000
OAUTH_TESTER_OAUTH__REDIRECT_PATH=/auth/callback
OAUTH_TESTER_OAUTH__CLIENT_ID=...
OAUTH_TESTER_OAUTH__CLIENT_SECRET=...
OAUTH_TESTER_OAUTH__SCOPES=openid profile email
OAUTH_TESTER_OAUTH__OIDC_DISCOVERY_URL=https://<thread-issuer>/.well-known/openid-configuration

# Or manual if discovery is not available
# OAUTH_TESTER_OAUTH__AUTHORIZE_URL=...
# OAUTH_TESTER_OAUTH__TOKEN_URL=...
# OAUTH_TESTER_OAUTH__JWKS_URL=...

OAUTH_TESTER_OAUTH__SSL_CERTFILE=certs/localhost.crt
OAUTH_TESTER_OAUTH__SSL_KEYFILE=certs/localhost.key
```

## Run
```
make run
```

Open `https://localhost:8000`, click Login, complete the flow, and copy the ID token or inspect parsed claims.

