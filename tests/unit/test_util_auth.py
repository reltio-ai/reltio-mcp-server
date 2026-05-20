"""Unit tests for src.util.auth (token file, refresh, client_credentials fallback)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.util import auth as auth_mod


class TestUtilAuth(unittest.TestCase):
    def setUp(self):
        self._old_environ = os.environ.copy()
        for k in (
            "RELTIO_TOKEN_FILE",
            "RELTIO_OAUTH_TOKEN_FILE",
            "RELTIO_AUTH_SERVER",
        ):
            os.environ.pop(k, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_environ)

    @patch("src.util.auth.requests.post")
    def test_get_access_token_client_credentials_only(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "cc-token"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        token = auth_mod.get_access_token()
        self.assertEqual(token, "cc-token")
        mock_post.assert_called_once()
        self.assertIn("client_credentials", mock_post.call_args[0][0])

    @patch("src.util.auth.time.time", return_value=1_700_000_000.0)
    def test_get_access_token_from_file_fresh(self, _mock_time):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            path = f.name
            json.dump(
                {
                    "access_token": "file-access",
                    "refresh_token": "r1",
                    "expires_in": 3600,
                    "_updated_at": int(1_700_000_000.0) - 100,
                },
                f,
            )
        try:
            os.environ["RELTIO_TOKEN_FILE"] = path
            tok = auth_mod.get_access_token()
            self.assertEqual(tok, "file-access")
        finally:
            os.unlink(path)

    @patch("src.util.auth.requests.post")
    @patch("src.util.auth.time.time")
    def test_get_access_token_refreshes_when_expired(self, mock_time, mock_post):
        now = 1_700_000_000.0
        old_ts = int(now - 5000)  # way past expiry
        mock_time.return_value = now

        def post_side_effect(url, **kwargs):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = {
                "access_token": "refreshed",
                "expires_in": 3600,
                "refresh_token": "new-rt",
            }
            m.raise_for_status = MagicMock()
            return m

        mock_post.side_effect = post_side_effect

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            path = f.name
            json.dump(
                {
                    "access_token": "stale",
                    "refresh_token": "rt-ok",
                    "expires_in": 3600,
                    "_updated_at": old_ts,
                },
                f,
            )
        try:
            os.environ["RELTIO_TOKEN_FILE"] = path
            out = auth_mod.get_access_token()
            self.assertEqual(out, "refreshed")
            with Path(path).open() as r:
                data = json.load(r)
            self.assertEqual(data["access_token"], "refreshed")
        finally:
            os.unlink(path)

    def test_get_access_token_expired_no_refresh_token_raises(self):
        with patch("src.util.auth.time.time", return_value=1_700_000_000.0):
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
                path = f.name
                json.dump(
                    {
                        "access_token": "stale",
                        "expires_in": 3600,
                        "_updated_at": 1,  # expired
                    },
                    f,
                )
            try:
                os.environ["RELTIO_OAUTH_TOKEN_FILE"] = path
                with self.assertRaises(ValueError) as ctx:
                    auth_mod.get_access_token()
                self.assertIn("refresh_token", str(ctx.exception).lower())
            finally:
                os.unlink(path)
