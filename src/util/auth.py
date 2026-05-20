"""Reltio API access token handling for Platform MCP.

Prefers a browser/OAuth token file (``RELTIO_TOKEN_FILE`` or
``RELTIO_OAUTH_TOKEN_FILE``) with auto-refresh via ``refresh_token`` when the
access token is expired. Falls back to client_credentials when no token file
is configured (e.g. machine-only deployments).

Many OAuth client configurations used for end-user/Postman flows do *not*
allow the client_credentials grant; in that case ensure a token file is set
and populated via the interactive OAuth step for your project.
"""
from __future__ import annotations

import base64
import json
import os
import threading
import time
from pathlib import Path

import requests

from src.constants import HEADER_SOURCE_TAG
from src.env import (
    RELTIO_AUTH_SERVER,
    RELTIO_CLIENT_BASIC_TOKEN,
    RELTIO_CLIENT_ID,
    RELTIO_CLIENT_SECRET,
)

_TOKEN_LOCK = threading.Lock()
_REFRESH_SKEW_SECONDS = 60


def _token_file_path() -> Path | None:
    raw = os.getenv("RELTIO_TOKEN_FILE") or os.getenv("RELTIO_OAUTH_TOKEN_FILE")
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p


def _load_token_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_token_file(path: Path, token: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(token, f, indent=2)
    os.replace(tmp, path)


def _token_expired(token: dict) -> bool:
    updated = float(token.get("_updated_at") or 0)
    expires_in = float(token.get("expires_in") or 0)
    if not updated or not expires_in:
        return True
    return (time.time() - updated) >= (expires_in - _REFRESH_SKEW_SECONDS)


def _refresh_with_refresh_token(token: dict) -> dict:
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            "token file missing refresh_token; re-run the Project OAuth / browser "
            "flow for your Reltio MCP and write a new token file."
        )
    url = f"{RELTIO_AUTH_SERVER.rstrip('/')}/oauth/token"
    basic = base64.b64encode(f"{RELTIO_CLIENT_ID}:{RELTIO_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise ValueError(f"refresh_token exchange failed {resp.status_code}: {resp.text}")
    new_token = resp.json()
    merged = {**token, **new_token, "_updated_at": int(time.time())}
    if "refresh_token" not in new_token:
        merged["refresh_token"] = refresh_token
    return merged


def _client_credentials_token() -> str:
    auth_url = f"{RELTIO_AUTH_SERVER.rstrip('/')}/oauth/token?grant_type=client_credentials"
    try:
        resp = requests.post(
            auth_url, headers={"Authorization": f"Basic {RELTIO_CLIENT_BASIC_TOKEN}"}, timeout=60
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except requests.exceptions.RequestException as e:
        err = getattr(getattr(e, "response", None), "text", None) or str(e)
        raise ValueError(f"Authentication failed: {err}")


def get_access_token() -> str:
    """Return a valid bearer token for Reltio API calls."""
    tf = _token_file_path()
    if tf and tf.is_file():
        with _TOKEN_LOCK:
            token = _load_token_file(tf)
            if _token_expired(token):
                token = _refresh_with_refresh_token(token)
                _save_token_file(tf, token)
            access = token.get("access_token")
            if not access:
                raise ValueError(f"token file at {tf} missing access_token")
            return access
    return _client_credentials_token()


def get_reltio_headers() -> dict:
    """Auth + default headers for Reltio API requests."""
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Source": HEADER_SOURCE_TAG,
    }
