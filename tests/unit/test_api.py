import unittest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError

from src.util.api import (
    http_request,
    extract_entity_id,
    extract_relation_id,
    extract_name,
    validate_connection_security,
    create_error_response,
    SecurityError,
    ALLOWED_ORIGINS,
    DEFAULT_TIMEOUT
)

class TestUtils(unittest.TestCase):

    def test_extract_entity_id(self):
        self.assertEqual(extract_entity_id("https://url/entity/123ABC"), "123ABC")
        self.assertEqual(extract_entity_id(None), "N/A")

    def test_extract_relation_id(self):
        self.assertEqual(extract_relation_id("https://url/relation/rel456"), "rel456")
        self.assertEqual(extract_relation_id(""), "N/A")

    def test_extract_name(self):
        attributes = {"Name": [{"value": "Alice"}]}
        self.assertEqual(extract_name(attributes), "Alice")
        self.assertEqual(extract_name({}), "N/A")
        self.assertEqual(extract_name({"Name": []}), "N/A")

    def test_validate_connection_security_https(self):
        url = "https://secure.url/path"
        headers = {"Origin": ALLOWED_ORIGINS[0]}
        self.assertTrue(validate_connection_security(url, headers))

    def test_validate_connection_security_insecure(self):
        url = "http://insecure.url"
        headers = {}
        with self.assertRaises(SecurityError):
            validate_connection_security(url, headers)

    def test_validate_connection_security_invalid_origin(self):
        url = "https://secure.url"
        headers = {"Origin": "http://malicious.site"}
        with self.assertRaises(SecurityError):
            validate_connection_security(url, headers)

    def test_create_error_response_sanitizes_details(self):
        details = {"field": "name", "error_type": "invalid", "extra": "not included"}
        response = create_error_response("VALIDATION_ERROR", "Bad request", details)
        self.assertIn("field", response["error"]["details"])
        self.assertNotIn("extra", response["error"]["details"])

    @patch('requests.request')
    def test_http_request_get_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = http_request('https://example.com')
        self.assertEqual(result, {'success': True})
        mock_request.assert_called_once_with(
            method='GET',
            url='https://example.com',
            params=None,
            json=None,
            headers=None,
            timeout=DEFAULT_TIMEOUT
        )

    @patch('requests.request')
    def test_http_request_post_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = http_request(url='https://example.com', method='POST')
        self.assertEqual(result, {'success': True})
        mock_request.assert_called_once_with(
            method='POST',
            url='https://example.com',
            params=None,
            json=None,
            headers=None,
            timeout=DEFAULT_TIMEOUT
        )

    @patch('requests.request')
    def test_http_request_raises_value_error_on_http_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            http_request('https://example.com')
        self.assertIn('API request failed: 404', str(context.exception))
