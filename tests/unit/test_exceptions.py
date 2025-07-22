import unittest
from src.util.exceptions import (
    ReltioApiError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    SecurityError,
    TimeoutError
)

class TestReltioExceptions(unittest.TestCase):

    def test_reltio_api_error(self):
        err = ReltioApiError(500, "Something went wrong", {"key": "value"})
        self.assertEqual(err.code, 500)
        self.assertEqual(err.message, "Something went wrong")
        self.assertEqual(err.details, {"key": "value"})
        self.assertIn("500: Something went wrong", str(err))

    def test_validation_error(self):
        err = ValidationError("Invalid input", field="email", details={"field": "email"})
        self.assertEqual(err.code, 400)
        self.assertEqual(err.message, "Invalid input")
        self.assertEqual(err.field, "email")
        self.assertEqual(err.details, {"field": "email"})

    def test_authentication_error(self):
        err = AuthenticationError("Token expired", {"reason": "expired"})
        self.assertEqual(err.code, 401)
        self.assertEqual(err.message, "Token expired")
        self.assertEqual(err.details, {"reason": "expired"})

    def test_authorization_error(self):
        err = AuthorizationError("Not allowed", {"role": "user"})
        self.assertEqual(err.code, 403)
        self.assertEqual(err.message, "Not allowed")
        self.assertEqual(err.details, {"role": "user"})

    def test_resource_not_found_error(self):
        err = ResourceNotFoundError("Entity", "12345", {"source": "database"})
        self.assertEqual(err.code, 404)
        self.assertIn("Entity with ID 12345 not found", err.message)
        self.assertEqual(err.details, {"source": "database"})

    def test_security_error_logs_safe_message(self):
        err = SecurityError("Origin not allowed", {"origin": "http://bad.com"})
        self.assertEqual(err.code, 403)
        self.assertEqual(err.message, "Security requirements not met")

    def test_timeout_error(self):
        err = TimeoutError("FetchData", 10, {"url": "/api/data"})
        self.assertEqual(err.code, 408)
        self.assertIn("FetchData timed out after 10 seconds", err.message)
        self.assertEqual(err.details, {"url": "/api/data"})
