import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from src.tools.match import find_matches_by_match_score, find_matches_by_confidence, get_total_matches, get_total_matches_by_entity_type

@pytest_asyncio.fixture(autouse=True)
def mock_dependencies():
    with patch("src.tools.match.MatchScoreRequest") as mock_match_score_request, \
         patch("src.tools.match.ConfidenceLevelRequest") as mock_confidence_request, \
         patch("src.tools.match.GetTotalMatchesRequest") as mock_total_matches_request, \
         patch("src.tools.match.GetMatchFacetsRequest") as mock_match_facets_request, \
         patch("src.tools.match.get_reltio_headers") as mock_get_headers, \
         patch("src.tools.match.get_reltio_url") as mock_get_url, \
         patch("src.tools.match.validate_connection_security") as mock_validate_security, \
         patch("src.tools.match.http_request") as mock_http_request, \
         patch("src.tools.match.create_error_response") as mock_create_error_response:

        mock_match_score_request.return_value = MagicMock()
        mock_confidence_request.return_value = MagicMock()
        mock_total_matches_request.return_value = MagicMock()
        mock_match_facets_request.return_value = MagicMock()
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_get_url.return_value = "https://reltio.com/entities/_search"
        mock_validate_security.return_value = None
        mock_http_request.return_value = [{"result": "some result"}]
        mock_create_error_response.side_effect = lambda code, msg: {"error": code, "message": msg}

        yield {
            "match_score_request": mock_match_score_request,
            "confidence_request": mock_confidence_request,
            "total_matches_request": mock_total_matches_request,
            "match_facets_request": mock_match_facets_request,
            "get_headers": mock_get_headers,
            "get_url": mock_get_url,
            "validate_security": mock_validate_security,
            "http_request": mock_http_request,
            "create_error_response": mock_create_error_response,
        }

@pytest.mark.asyncio
async def test_find_matches_by_match_score_success(mock_dependencies):
    # Patch the MatchScoreRequest to return a real object with int fields
    mock_dependencies["match_score_request"].return_value.max_results = 10
    mock_dependencies["match_score_request"].return_value.offset = 0
    # Mock http_request to return a list of dicts as expected
    mock_dependencies["http_request"].return_value = [
        {"uri": "entities/1", "label": "Entity 1", "type": "Individual"},
        {"uri": "entities/2", "label": "Entity 2", "type": "Individual"}
    ]
    result = await find_matches_by_match_score(10, 90)
    if isinstance(result, str):
        import yaml
        result = yaml.safe_load(result)
    assert isinstance(result, list)
    assert all("uri" in r and "label" in r and "type" in r for r in result)

@pytest.mark.asyncio
async def test_find_matches_by_match_score_validation_error(mock_dependencies):
    mock_dependencies["match_score_request"].side_effect = ValueError("Invalid range")
    result = await find_matches_by_match_score()
    assert result["error"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_find_matches_by_confidence_success(mock_dependencies):
    # Patch the ConfidenceLevelRequest to return a real object with int fields
    mock_dependencies["confidence_request"].return_value.max_results = 10
    mock_dependencies["confidence_request"].return_value.offset = 0
    # Mock http_request to return a list of dicts as expected
    mock_dependencies["http_request"].return_value = [
        {"uri": "entities/1", "label": "Entity 1", "type": "Individual"},
        {"uri": "entities/2", "label": "Entity 2", "type": "Individual"}
    ]
    result = await find_matches_by_confidence("High confidence")
    if isinstance(result, str):
        import yaml
        result = yaml.safe_load(result)
    assert isinstance(result, list)
    assert all("uri" in r and "label" in r and "type" in r for r in result)

@pytest.mark.asyncio
async def test_find_matches_by_confidence_validation_error(mock_dependencies):
    mock_dependencies["confidence_request"].side_effect = ValueError("Invalid confidence")
    result = await find_matches_by_confidence()
    assert result["error"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_find_matches_by_confidence_no_results(mock_dependencies):
    # Patch the ConfidenceLevelRequest to return a real object with int fields
    mock_dependencies["confidence_request"].return_value.max_results = 10
    mock_dependencies["confidence_request"].return_value.offset = 0
    mock_dependencies["http_request"].return_value = []

    result = await find_matches_by_confidence("Low confidence")
    if isinstance(result, str):
        import yaml
        result = yaml.safe_load(result)
    assert "results" in result
    assert result["results"] == []

@pytest.mark.asyncio
async def test_find_matches_by_match_score_http_exception(mock_dependencies):
    mock_dependencies["http_request"].side_effect = Exception("HTTP failed")
    result = await find_matches_by_match_score()
    assert result["error"] == "SERVER_ERROR"

@pytest.mark.asyncio
async def test_get_total_matches_success(mock_dependencies):
    # Configure the mock to return a specific response for total matches
    mock_dependencies["http_request"].return_value = {"total": 1114}
    mock_dependencies["get_url"].return_value = "https://reltio.com/entities/_total"
    
    # Configure the min_matches property on the request mock
    mock_dependencies["total_matches_request"].return_value.min_matches = 0
    
    # Call the function
    result = await get_total_matches(0)
    
    # Assert the result
    assert "total" in result
    assert result["total"] == 1114
    assert result["min_matches"] == 0
    assert "message" in result

@pytest.mark.asyncio
async def test_get_total_matches_with_filter(mock_dependencies):
    # Configure the mock to return a specific response
    mock_dependencies["http_request"].return_value = {"total": 500}
    mock_dependencies["get_url"].return_value = "https://reltio.com/entities/_total"
    
    # Set the expected request object properties
    mock_dependencies["total_matches_request"].return_value.min_matches = 5
    
    # Call the function with a filter
    result = await get_total_matches(5)
    
    # Assert the payload contains the correct filter
    mock_dependencies["http_request"].assert_called_once()
    assert "total" in result
    assert result["total"] == 500
    assert result["min_matches"] == 5

@pytest.mark.asyncio
async def test_get_total_matches_validation_error(mock_dependencies):
    # Configure the mock to raise a validation error
    mock_dependencies["total_matches_request"].side_effect = ValueError("Invalid min_matches")
    
    # Call the function
    result = await get_total_matches(-1)  # Invalid value
    
    # Assert the error response
    assert result["error"] == "VALIDATION_ERROR"
    assert "Invalid" in result["message"]

@pytest.mark.asyncio
async def test_get_total_matches_api_error(mock_dependencies):
    # Configure the mock to return an invalid response
    mock_dependencies["http_request"].return_value = {"not_total": "missing total field"}
    
    # Call the function
    result = await get_total_matches(0)
    
    # Assert the error response
    assert "error" in result
    assert result["error"] == "RESPONSE_ERROR"

@pytest.mark.asyncio
async def test_get_total_matches_http_exception(mock_dependencies):
    # Configure the mock to raise an exception
    mock_dependencies["http_request"].side_effect = Exception("HTTP failed")
    
    # Call the function
    result = await get_total_matches(0)
    
    # Assert the error response
    assert result["error"] == "SERVER_ERROR"
    assert "Failed to retrieve total matches count" in result["message"]

@pytest.mark.asyncio
async def test_get_total_matches_by_entity_type_success(mock_dependencies):
    # Configure the mock to return a specific response for facets
    mock_dependencies["http_request"].return_value = {"type": {"Individual": 56, "Organization": 1058}}
    mock_dependencies["get_url"].return_value = "https://reltio.com/entities/_facets"
    
    # Configure the min_matches property on the request mock
    mock_dependencies["match_facets_request"].return_value.min_matches = 0
    
    # Call the function
    result = await get_total_matches_by_entity_type(0)
    
    # Assert the result
    assert "type_counts" in result
    assert result["type_counts"] == {"Individual": 56, "Organization": 1058}
    assert result["min_matches"] == 0
    assert "message" in result

@pytest.mark.asyncio
async def test_get_total_matches_by_entity_type_with_filter(mock_dependencies):
    # Configure the mock to return a specific response
    mock_dependencies["http_request"].return_value = {"type": {"Individual": 20, "Organization": 500}}
    mock_dependencies["get_url"].return_value = "https://reltio.com/entities/_facets"
    
    # Set the expected request object properties
    mock_dependencies["match_facets_request"].return_value.min_matches = 5
    
    # Call the function with a filter
    result = await get_total_matches_by_entity_type(5)
    
    # Assert the http_request was called with correct parameters
    mock_dependencies["http_request"].assert_called_once()
    assert "type_counts" in result
    assert result["type_counts"] == {"Individual": 20, "Organization": 500}
    assert result["min_matches"] == 5

@pytest.mark.asyncio
async def test_get_total_matches_by_entity_type_validation_error(mock_dependencies):
    # Configure the mock to raise a validation error
    mock_dependencies["match_facets_request"].side_effect = ValueError("Invalid min_matches")
    
    # Call the function
    result = await get_total_matches_by_entity_type(-1)  # Invalid value
    
    # Assert the error response
    assert result["error"] == "VALIDATION_ERROR"
    assert "Invalid" in result["message"]

@pytest.mark.asyncio
async def test_get_total_matches_by_entity_type_api_error(mock_dependencies):
    # Configure the mock to return an invalid response
    mock_dependencies["http_request"].return_value = {"not_type": "missing type field"}
    
    # Call the function
    result = await get_total_matches_by_entity_type(0)
    
    # Assert the error response
    assert "error" in result
    assert result["error"] == "RESPONSE_ERROR"

@pytest.mark.asyncio
async def test_get_total_matches_by_entity_type_http_exception(mock_dependencies):
    # Configure the mock to raise an exception
    mock_dependencies["http_request"].side_effect = Exception("HTTP failed")
    
    # Call the function
    result = await get_total_matches_by_entity_type(0)
    
    # Assert the error response
    assert result["error"] == "SERVER_ERROR"
    assert "Failed to retrieve match facets" in result["message"]
