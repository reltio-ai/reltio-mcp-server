"""
Test cases for activity tools functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import unquote

from src.tools.activity import get_merge_activities
from src.constants import ERROR_CODES
from src.util.models import MergeActivitiesRequest
from src.util.exceptions import SecurityError

# Setup mock response data
MOCK_ACTIVITY_RESPONSE = {
    "items": [
        {
            "id": "activity1",
            "timestamp": 1744191663001,
            "user": "john.doe@example.com",
            "data": {
                "type": "ENTITIES_MERGED_MANUALLY",
                "sourceEntities": ["entity1", "entity2"],
                "resultEntity": "entity1"
            },
            "objectType": "configuration/entityTypes/Individual"
        },
        {
            "id": "activity2",
            "timestamp": 1744191663002,
            "user": "jane.doe@example.com",
            "data": {
                "type": "ENTITIES_MERGED",
                "sourceEntities": ["entity3", "entity4"],
                "resultEntity": "entity3"
            },
            "objectType": "configuration/entityTypes/Organization"
        }
    ],
    "total": 2
}

@pytest.mark.asyncio
class TestGetMergeActivities:
    """Test cases for the get_merge_activities function."""

    @patch("src.tools.activity.yaml.dump")
    @patch("src.tools.activity.http_request")
    @patch("src.tools.activity.get_reltio_headers")
    @patch("src.tools.activity.validate_connection_security")
    async def test_get_merge_activities_success(
        self,
        mock_validate_security,
        mock_get_headers,
        mock_http_request,
        mock_yaml_dump
    ):
        """Test successful retrieval of merge activities."""
        # Setup mocks
        mock_validate_security.return_value = None
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_http_request.return_value = MOCK_ACTIVITY_RESPONSE
        mock_yaml_dump.return_value = "mocked_yaml_output"

        # Call the function
        result = await get_merge_activities(
            timestamp_gt=1744191663000,
            event_types=["ENTITIES_MERGED_MANUALLY", "ENTITIES_MERGED"],
            entity_type="Individual",
            tenant_id="test_tenant"
        )

        # Assertions
        assert result == "mocked_yaml_output"
        mock_validate_security.assert_called_once()
        mock_get_headers.assert_called_once()
        mock_http_request.assert_called_once()
        mock_yaml_dump.assert_called_once_with(MOCK_ACTIVITY_RESPONSE, sort_keys=False)

        
        # Verify the URL contains the correct filter parameters
        call_args = mock_http_request.call_args
        url = call_args[0][0]
        assert "gt(timestamp,1744191663000)" in unquote(url)
        assert "ENTITIES_MERGED_MANUALLY" in url
        assert "ENTITIES_MERGED" in url
        assert "Individual" in url

    @patch("src.tools.activity.validate_connection_security")
    async def test_get_merge_activities_validation_error(self, mock_validate_security):
        """Test merge activities retrieval with validation error."""
        # Call the function with invalid parameters (negative timestamp)
        result = await get_merge_activities(
            timestamp_gt=-1,  # Invalid timestamp
            tenant_id="test_tenant"
        )

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "VALIDATION_ERROR"
        mock_validate_security.assert_not_called()

    @patch("src.tools.activity.http_request")
    @patch("src.tools.activity.get_reltio_headers")
    @patch("src.tools.activity.validate_connection_security")
    async def test_get_merge_activities_security_validation_failure(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test merge activities retrieval with security validation failure."""
        # Setup mocks
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate_security.side_effect = SecurityError("Security validation failed")
        
        # Call the function
        result = await get_merge_activities(
            timestamp_gt=1744191663000,
            tenant_id="test_tenant"
        )
        
        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "AUTHORIZATION_ERROR"
        assert mock_validate_security.called
        mock_get_headers.assert_called_once_with()
        mock_http_request.assert_not_called()

    @patch("src.tools.activity.http_request")
    @patch("src.tools.activity.get_reltio_headers")
    @patch("src.tools.activity.validate_connection_security")
    async def test_get_merge_activities_api_error(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test merge activities retrieval with API error."""
        # Setup mocks
        mock_validate_security.return_value = {"success": True}
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        
        # Simulate an API error by making the http_request raise an exception
        mock_http_request.side_effect = Exception("400 Bad Request")

        # Call the function
        result = await get_merge_activities(
            timestamp_gt=1744191663000,
            tenant_id="test_tenant"
        )

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "SERVER_ERROR"
        # Verify validate_connection_security was called (without checking exact parameters)
        assert mock_validate_security.called
        # Verify the other mocks were called
        mock_get_headers.assert_called_once_with()
        assert mock_http_request.called

    @patch("src.tools.activity.http_request")
    @patch("src.tools.activity.get_reltio_headers")
    @patch("src.tools.activity.validate_connection_security")
    async def test_get_merge_activities_exception(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test merge activities retrieval with exception."""
        # Setup mocks
        mock_validate_security.return_value = {"success": True}
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_http_request.side_effect = Exception("Test exception")

        # Call the function
        result = await get_merge_activities(
            timestamp_gt=1744191663000,
            tenant_id="test_tenant"
        )

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "SERVER_ERROR"
        # Verify validate_connection_security was called (without checking exact parameters)
        assert mock_validate_security.called
        # Verify the other mocks were called with expected parameters
        mock_get_headers.assert_called_once_with()
        assert mock_http_request.called 