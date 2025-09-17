# OAuth Flow Sequence

The diagram below summarizes the interactive login flow implemented by the OAuth Tester application, including optional paths for OIDC verification, user info retrieval, and Threads long-lived token handling.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Browser
    participant App as OAuth Tester (FastAPI)
    participant Client as OAuth HTTP Client
    participant Provider as OAuth Provider
    participant Threads as Threads Graph API

    User->>Browser: Click "Login with Provider"
    Browser->>App: GET /auth/login
    App->>App: Generate state, nonce?, code_verifier?
    App->>Client: build_authorization_url(state, nonce?, PKCE?)
    Client-->>App: Authorization URL
    App-->>Browser: HTTP 302 -> Provider authorize URL
    Browser->>Provider: GET /authorize with state (+PKCE)
    Provider-->>Browser: Present auth & consent UI
    User->>Provider: Authenticate and grant consent
    Provider-->>Browser: 302 /auth/callback?code&state
    Browser->>App: GET /auth/callback?code&state

    alt Authorization error from provider
        App->>App: Persist error details in session
        App-->>Browser: 302 Redirect to "/"
    else Authorization code supplied
        App->>App: Validate state from session
        App->>Client: exchange_code(code, redirect_uri, code_verifier?)
        Client->>Provider: POST /token (httpx)
        Provider-->>Client: Token response (access_token, id_token?)
        Client-->>App: OAuth tokens payload
        opt ID token present
            App->>Client: parse_id_token(id_token, nonce)
            Client-->>App: OIDC claims (JWKS verified)
        end
        opt Access token only + userinfo configured
            App->>Provider: GET userinfo(access_token, fields?, appsecret_proof?)
            Provider-->>App: Profile JSON
        end
        opt Threads auto long-lived exchange enabled
            App->>Threads: GET /access_token (th_exchange_token)
            Threads-->>App: Long-lived token payload
        end
        App->>App: Persist tokens/claims/profile, clear transient state
        App-->>Browser: 302 Redirect to "/"
    end

    Browser->>App: GET /
    App-->>Browser: Render tokens dashboard (ID token, access token, errors)
```

## Implementation Notes

- The `/auth/login` handler sets the session `state`, optional `nonce`, and PKCE `code_verifier` before asking the manual OAuth client to build an authorization URL, which is returned as a `302` redirect.
- The `/auth/callback` handler validates state, extracts the authorization code, performs the authorization code exchange via `httpx`, and stores resulting tokens, claims, and profile data in the session.
- OIDC providers have ID tokens verified against the configured JWKS (either discovered or manually supplied), with nonce validation handled in the client.
- Non-OIDC providers can expose a user profile by calling the configured or discovered `userinfo_endpoint` with the access token (and optional `appsecret_proof`).
- Threads-specific logic can automatically exchange or refresh long-lived tokens via the Meta Threads Graph API.
- Any upstream errors (provider redirect errors or token exchange failures) are captured in the session and surfaced on the home view.
