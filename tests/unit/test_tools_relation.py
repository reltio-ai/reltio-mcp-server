import pytest
from unittest.mock import patch, MagicMock
from src.tools.relation import get_relation_details

@pytest.mark.asyncio
async def test_get_relation_details_success():
    with patch("src.tools.relation.RelationIdRequest") as mock_request, \
         patch("src.tools.relation.get_reltio_url") as mock_url, \
         patch("src.tools.relation.get_reltio_headers") as mock_headers, \
         patch("src.tools.relation.validate_connection_security") as mock_validate, \
         patch("src.tools.relation.http_request") as mock_http:

        mock_request.return_value = MagicMock(relation_id="rel123", tenant_id="tenant")
        mock_url.return_value = "https://reltio.com/relations/rel123"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"id": "rel123", "type": "relation", "attributes": {}}

        result = await get_relation_details("rel123", "tenant")
        import yaml
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["id"] == "rel123"

@pytest.mark.asyncio
async def test_get_relation_details_validation_error():
    with patch("src.tools.relation.RelationIdRequest", side_effect=ValueError("Invalid ID")), \
         patch("src.tools.relation.create_error_response") as mock_create_error:
        
        mock_create_error.return_value = {"error": "VALIDATION_ERROR", "message": "Invalid relation ID format: Invalid ID"}

        result = await get_relation_details("bad-id")
        assert result["error"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_get_relation_details_authentication_error():
    with patch("src.tools.relation.RelationIdRequest") as mock_request, \
         patch("src.tools.relation.get_reltio_url"), \
         patch("src.tools.relation.get_reltio_headers", side_effect=Exception("Auth failed")), \
         patch("src.tools.relation.create_error_response") as mock_create_error:
        
        mock_request.return_value = MagicMock(relation_id="rel123", tenant_id="tenant")
        mock_create_error.return_value = {"error": "AUTHENTICATION_ERROR", "message": "Failed to authenticate with Reltio API"}

        result = await get_relation_details("rel123")
        assert result["error"] == "AUTHENTICATION_ERROR"

@pytest.mark.asyncio
async def test_get_relation_details_404_not_found():
    with patch("src.tools.relation.RelationIdRequest") as mock_request, \
         patch("src.tools.relation.get_reltio_url"), \
         patch("src.tools.relation.get_reltio_headers"), \
         patch("src.tools.relation.validate_connection_security"), \
         patch("src.tools.relation.http_request", side_effect=Exception("404 Not Found")), \
         patch("src.tools.relation.create_error_response") as mock_create_error:

        mock_request.return_value = MagicMock(relation_id="rel123", tenant_id="tenant")
        mock_create_error.return_value = {"error": "RESOURCE_NOT_FOUND", "message": "Relation with ID rel123 not found"}

        result = await get_relation_details("rel123")
        assert result["error"] == "RESOURCE_NOT_FOUND"

@pytest.mark.asyncio
async def test_get_relation_details_generic_server_error():
    with patch("src.tools.relation.RelationIdRequest") as mock_request, \
         patch("src.tools.relation.get_reltio_url"), \
         patch("src.tools.relation.get_reltio_headers"), \
         patch("src.tools.relation.validate_connection_security"), \
         patch("src.tools.relation.http_request", side_effect=Exception("Some API error")), \
         patch("src.tools.relation.create_error_response") as mock_create_error:

        mock_request.return_value = MagicMock(relation_id="rel123", tenant_id="tenant")
        mock_create_error.return_value = {"error": "SERVER_ERROR", "message": "Failed to retrieve relation details from Reltio API"}

        result = await get_relation_details("rel123")
        assert result["error"] == "SERVER_ERROR"

@pytest.mark.asyncio
async def test_get_relation_details_unexpected_error():
    with patch("src.tools.relation.RelationIdRequest", side_effect=Exception("Boom")), \
         patch("src.tools.relation.create_error_response") as mock_create_error:
        
        mock_create_error.return_value = {"error": "SERVER_ERROR", "message": "An unexpected error occurred while retrieving relation details"}

        result = await get_relation_details("rel123")
        assert result["error"] == "SERVER_ERROR"
