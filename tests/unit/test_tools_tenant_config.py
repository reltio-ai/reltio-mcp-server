import pytest
from unittest.mock import patch

from src.tools.tenant_config import get_business_configuration, get_tenant_permissions_metadata

TENANT_ID = "test-tenant"

@pytest.mark.asyncio
class TestBusinessConfig:
    @patch("src.tools.tenant_config.http_request")
    @patch("src.tools.tenant_config.validate_connection_security")
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_successful_response(self, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_get_url.return_value = "https://reltio.api/entities/123ABC"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {}
        result = await get_business_configuration(TENANT_ID)
        assert isinstance(result, dict)

    @patch("src.tools.tenant_config.http_request")
    @patch("src.tools.tenant_config.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_authentication_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await get_business_configuration(TENANT_ID)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.tenant_config.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.tenant_config.validate_connection_security")
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_server_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await get_business_configuration(TENANT_ID)
        assert result["error"]["code_key"] == "API_REQUEST_ERROR"

@pytest.mark.asyncio
class TestTenantPermissionsMetadata:
    @patch("src.tools.tenant_config.http_request")
    @patch("src.tools.tenant_config.validate_connection_security")
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_successful_response(self, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_get_url.return_value = "https://reltio.api/entities/123ABC"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"status": "completed"}

        result = await get_tenant_permissions_metadata(TENANT_ID)
        import yaml
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert isinstance(result, dict)
        assert result["status"] == "completed"

    @patch("src.tools.tenant_config.http_request")
    @patch("src.tools.tenant_config.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_authentication_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await get_tenant_permissions_metadata(TENANT_ID)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.tenant_config.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.tenant_config.validate_connection_security")
    @patch("src.tools.tenant_config.get_reltio_headers")
    @patch("src.tools.tenant_config.get_reltio_url")
    async def test_server_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await get_tenant_permissions_metadata(TENANT_ID)
        assert result["error"]["code_key"] == "API_REQUEST_ERROR"
