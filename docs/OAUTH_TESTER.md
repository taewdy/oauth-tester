# OAuth Tester

Local HTTPS OAuth/OIDC tester built with FastAPI. Implements Authorization Code + PKCE with state and nonce, and displays ID token (JWT), access token, and parsed claims.

## Features
- Auth Code + PKCE, state, nonce
- OIDC discovery or manual endpoints
- Local HTTPS via self-signed certs
- Minimal UI to view/copy tokens and claims
- Env-driven config via `OAUTH_TESTER_*`

## Setup
1) Copy env and fill values
```
cp .env.example .env
```

2) Generate local TLS certs
```
make certs
```

3) Configure env
- Required: `OAUTH_TESTER_OAUTH__CLIENT_ID`
- Optional but common: `OAUTH_TESTER_OAUTH__CLIENT_SECRET`
- Discovery OR manual endpoints:
  - Discovery: `OAUTH_TESTER_OAUTH__OIDC_DISCOVERY_URL`
  - Manual: `OAUTH_TESTER_OAUTH__AUTHORIZE_URL`, `OAUTH_TESTER_OAUTH__TOKEN_URL`, `OAUTH_TESTER_OAUTH__JWKS_URL`
- HTTPS and redirect:
  - `OAUTH_TESTER_OAUTH__BASE_URL=https://localhost:8000`
  - `OAUTH_TESTER_OAUTH__REDIRECT_PATH=/auth/callback`
  - `OAUTH_TESTER_OAUTH__SSL_CERTFILE=certs/localhost.crt`
  - `OAUTH_TESTER_OAUTH__SSL_KEYFILE=certs/localhost.key`

4) Run
```
make run
```
Open `https://localhost:8000` and complete the login flow.

## Thread Provider
Configure your Thread app with:
- Redirect URI: `https://localhost:8000/auth/callback`
- Scopes: `openid profile email`
- Enable Authorization Code + PKCE
- Discovery preferred; otherwise provide the manual endpoints

## Docker
```
docker compose up --build
```
Set env keys inside `docker-compose.yml` to pass credentials and TLS paths.

