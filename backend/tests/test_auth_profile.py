from __future__ import annotations

import unittest
from pathlib import Path
import sys

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.auth_profile import AuthProfileCreate

try:
    from app.core.security import decrypt_secret, encrypt_secret
except ModuleNotFoundError:
    decrypt_secret = None
    encrypt_secret = None


class AuthProfileTests(unittest.TestCase):
    def test_auth_profile_rejects_invalid_login_url(self) -> None:
        with self.assertRaises(ValidationError):
            AuthProfileCreate(
                name="Bad Login",
                auth_type="form",
                login_url="file:///tmp/login.html",
            )

    def test_optional_fields_are_stripped(self) -> None:
        profile = AuthProfileCreate(
            name=" Staging Login ",
            auth_type="form",
            login_url=" https://example.com/login/ ",
            username_selector=" input[name=email] ",
            password_selector=" ",
            is_active=True,
        )
        self.assertEqual(profile.login_url, "https://example.com/login")
        self.assertEqual(profile.username_selector, "input[name=email]")
        self.assertIsNone(profile.password_selector)

    def test_secret_encryption_round_trip(self) -> None:
        if encrypt_secret is None or decrypt_secret is None:
            self.skipTest("Backend crypto dependencies are not installed in this local Python runtime.")
        encrypted = encrypt_secret("secret-password")
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, "secret-password")
        self.assertEqual(decrypt_secret(encrypted), "secret-password")


if __name__ == "__main__":
    unittest.main()
