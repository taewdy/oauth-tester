# Type Checking Notes

This document captures the key decisions we made while wiring up type safety for the
OAuth client integration.

## Authlib Client Typing
- FastAPI injects the Authlib client into the auth routes. Authlib returns an object that
  behaves like `StarletteOAuth2App`, exposing methods such as `authorize_redirect` and
  `authorize_access_token`.
- Instead of relying on that concrete class, we define an `OAuthClient` `Protocol` that
  describes only the methods the routes consume. `get_oauth_client` advertises the
  protocol, and the handlers depend on it, which keeps the production code free of casts
  while allowing tests to swap in fakes.
- Runtime code stays functional: the dependency injection simply passes the client as a
  function parameter, keeping the auth handlers stateless and testable.

## Mypy Configuration
- We already ship a `make type-check` target; enabling it only required adding a
  `[tool.mypy]` section to `pyproject.toml`.
- Configuration highlights:
  - Python 3.11 target and the `pydantic.mypy` plugin so models continue to type-check.
  - `disallow_untyped_defs` and `check_untyped_defs` enforce explicit annotations.
  - `authlib.*` modules are ignored for missing type hints (Authlib does not ship stub
    files).
- Run locally via `uv run mypy src/` or `make type-check`.

- **Protocol vs casts** – We briefly guarded the Authlib client with `isinstance`
  checks plus `cast`, but that adds runtime logic purely for the type checker. Defining a
  protocol avoids the guard and keeps the dependency surface explicit. If we ever need
  broader coverage, stub files remain an option.
- `typing.Protocol` lives in the standard library, similar to Go interfaces: structural
  typing with no runtime cost. Static analyzers (mypy, pyright, etc.) enforce the
  contract.

## Practical Guidelines
- Treat `Any` as a last resort; contain it to narrow scopes when untyped third-party
  APIs demand it.
- Prefer defining protocols on the consumer side so test doubles can implement the same
  contract.
- Keep dependency injection in FastAPI routes—receiving the client through a parameter
  keeps the design functional while remaining DI-friendly for overrides in tests.
- If we need additional tooling integration, consider running `make type-check` in CI to
  keep drift from creeping in.
