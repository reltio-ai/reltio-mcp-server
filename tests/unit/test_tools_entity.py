import pytest
from unittest.mock import patch
import yaml

from src.tools.entity import (
    get_entity_details, 
    update_entity_attributes, 
    get_entity_match_history, 
    get_entity_matches, 
    merge_entities, 
    reject_entity_match, 
    export_merge_tree,
    unmerge_entity_by_contributor,
    unmerge_entity_tree_by_contributor
)

ENTITY_ID = "123ABC"
TENANT_ID = "test-tenant"

@pytest.mark.asyncio
class TestGetEntityDetails:
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_successful_response(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/123ABC"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"id": ENTITY_ID, "name": "Test Entity"}

        result = await get_entity_details(ENTITY_ID, {"attributes": []}, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert isinstance(parsed_result, (dict, list))

    @patch("src.tools.entity.EntityIdRequest", side_effect=ValueError("Invalid ID"))
    async def test_validation_error(self, _):
        result = await get_entity_details("!invalid_id!", {"attributes": []}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_authentication_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await get_entity_details(ENTITY_ID, {"attributes": []}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.entity.http_request", side_effect=Exception("404 Not Found"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_entity_not_found(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await get_entity_details(ENTITY_ID, {"attributes": []}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"

    @patch("src.tools.entity.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_server_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await get_entity_details(ENTITY_ID, {"attributes": []}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "SERVER_ERROR"

@pytest.mark.asyncio
class TestUpdateEntityAttributes:
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.UpdateEntityAttributesRequest")
    async def test_successful_response(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/123ABC"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"id": ENTITY_ID, "name": "Test Entity"}

        result = await update_entity_attributes(ENTITY_ID, {'attributes': {'FirstName': 'John'}}, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert isinstance(parsed_result, (dict, list))
        assert parsed_result["id"] == ENTITY_ID

    @patch("src.tools.entity.UpdateEntityAttributesRequest", side_effect=ValueError("Invalid ID"))
    async def test_validation_error(self, _):
        result = await update_entity_attributes("!invalid_id!", TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.UpdateEntityAttributesRequest")
    async def test_authentication_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await update_entity_attributes(ENTITY_ID, {'attributes': {'FirstName': 'John'}}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.entity.http_request", side_effect=Exception("404 Not Found"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.UpdateEntityAttributesRequest")
    async def test_entity_not_found(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await update_entity_attributes(ENTITY_ID, {'attributes': {'FirstName': 'John'}}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"

    @patch("src.tools.entity.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.UpdateEntityAttributesRequest")
    async def test_server_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_request_model.return_value.entity_id = ENTITY_ID
        mock_request_model.return_value.tenant_id = TENANT_ID

        result = await update_entity_attributes(ENTITY_ID, {'attributes': {'FirstName': 'John'}}, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "SERVER_ERROR"


@pytest.mark.asyncio
class TestGetEntityMatches:

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_successful_entity_matches(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.side_effect = [
            "https://api/entities/123ABC/_transitiveMatches",
            "https://api/entities/123ABC"
        ]
        mock_headers.return_value = {"Authorization": "Bearer token"}
        # format_entity_matches expects a list of dicts, so mock accordingly
        mock_http.side_effect = [
            [
                {"object": {"uri": "entities/match1"}, "matchRules": [], "createdTime": "2024-01-01T00:00:00Z", "matchScore": 95, "label": "Match 1"},
                {"object": {"uri": "entities/match2"}, "matchRules": [], "createdTime": "2024-01-01T00:00:00Z", "matchScore": 90, "label": "Match 2"}
            ],
            {"id": ENTITY_ID}
        ]

        result = await get_entity_matches(ENTITY_ID, TENANT_ID, max_results=10)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert "source_entity" in parsed_result
        assert len(parsed_result["matches"]) == 2

    @patch("src.tools.entity.EntityIdRequest", side_effect=ValueError("Invalid entity"))
    async def test_validation_error(self, _):
        result = await get_entity_matches("invalid", TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"

    @patch("src.tools.entity.get_reltio_headers", side_effect=Exception("Auth fail"))
    @patch("src.tools.entity.EntityIdRequest")
    async def test_auth_error(self, mock_req, _):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID

        result = await get_entity_matches(ENTITY_ID, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.entity.http_request", side_effect=Exception("404 Not Found"))
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_entity_not_found(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.return_value = "https://api/entities/123ABC/_transitiveMatches"

        result = await get_entity_matches(ENTITY_ID, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"

    @patch("src.tools.entity.http_request", side_effect=[[], {"id": ENTITY_ID}])
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_no_matches_found(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.return_value = "https://api/entities/123ABC/_transitiveMatches"

        result = await get_entity_matches(ENTITY_ID, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert "matches" in parsed_result
        assert parsed_result["matches"] == []

    @patch("src.tools.entity.http_request", side_effect=[["match1", "match2"], Exception("Source fetch failed")])
    @patch("src.tools.entity.get_reltio_url", side_effect=[
        "https://api/entities/123ABC/_transitiveMatches",
        "https://api/entities/123ABC"
    ])
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_source_entity_fetch_failure(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID

        result = await get_entity_matches(ENTITY_ID, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert "matches" in parsed_result
        assert "source_entity" not in parsed_result
        assert "could not retrieve source entity details" in parsed_result["message"]


@pytest.mark.asyncio
class TestGetEntityMatchHistory:

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_successful_match_history(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.side_effect = [
            "https://api/entities/123ABC/_crosswalkTree",
            "https://api/entities/123ABC"
        ]
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.side_effect = [
            [{"id": "match1"}],
            {"id": ENTITY_ID}
        ]

        result = await get_entity_match_history(ENTITY_ID, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert isinstance(parsed_result, (dict, list))

    @patch("src.tools.entity.EntityIdRequest", side_effect=ValueError("Invalid"))
    async def test_validation_error(self, _):
        result = await get_entity_match_history("invalid!", TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"

    @patch("src.tools.entity.get_reltio_headers", side_effect=Exception("Bad token"))
    @patch("src.tools.entity.EntityIdRequest")
    async def test_auth_error(self, mock_req, _):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID

        result = await get_entity_match_history(ENTITY_ID, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.entity.http_request", side_effect=Exception("404"))
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_entity_not_found(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.return_value = "https://api/entities/123ABC/_crosswalkTree"

        result = await get_entity_match_history(ENTITY_ID, TENANT_ID)
        if isinstance(result, str):
            result = yaml.safe_load(result)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"

    @patch("src.tools.entity.http_request", side_effect=[[], {"id": ENTITY_ID}])
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_no_match_history(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID
        mock_url.return_value = "https://api/entities/123ABC/_crosswalkTree"

        result = await get_entity_match_history(ENTITY_ID, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert "match_history" in parsed_result
        assert parsed_result["match_history"] == []

    @patch("src.tools.entity.http_request", side_effect=[[{"id": "h1"}], Exception("Source fetch error")])
    @patch("src.tools.entity.get_reltio_url", side_effect=[
        "https://api/entities/123ABC/_crosswalkTree",
        "https://api/entities/123ABC"
    ])
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.EntityIdRequest")
    async def test_source_entity_fetch_failure(self, mock_req, mock_headers, mock_security, mock_url, mock_http):
        mock_req.return_value.entity_id = ENTITY_ID
        mock_req.return_value.tenant_id = TENANT_ID

        result = await get_entity_match_history(ENTITY_ID, TENANT_ID)
        parsed_result = yaml.safe_load(result) if isinstance(result, str) else result
        assert "match_history" in parsed_result
        assert "could not retrieve source entity details" in parsed_result["message"]

@pytest.mark.asyncio
class TestMergeEntities:
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.MergeEntitiesRequest")
    async def test_successful_merge(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        entity_ids = ["entity1", "entity2"]
        formatted_ids = ["entities/entity1", "entities/entity2"]
        mock_request_model.return_value.entity_ids = formatted_ids
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/_same"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"id": "merged_entity_id", "status": "success"}
        result = await merge_entities(entity_ids, TENANT_ID)
        assert isinstance(result, dict)
        assert result["id"] == "merged_entity_id"
        assert result["status"] == "success"
        mock_http.assert_called_once_with(
            mock_get_url.return_value,
            method='POST',
            data=formatted_ids,
            headers=mock_headers.return_value
        )
    
    @patch("src.tools.entity.MergeEntitiesRequest", side_effect=ValueError("Invalid entity IDs"))
    async def test_validation_error(self, _):
        result = await merge_entities(["only_one_id"], TENANT_ID)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"
    
    @patch("src.tools.entity.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.MergeEntitiesRequest")
    async def test_authentication_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate):
        entity_ids = ["entity1", "entity2"]
        formatted_ids = ["entities/entity1", "entities/entity2"]
        mock_request_model.return_value.entity_ids = formatted_ids
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/_same"
        
        result = await merge_entities(entity_ids, TENANT_ID)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("404 Not Found"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.MergeEntitiesRequest")
    async def test_entity_not_found(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        entity_ids = ["entity1", "entity2"]
        formatted_ids = ["entities/entity1", "entities/entity2"]
        mock_request_model.return_value.entity_ids = formatted_ids
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/_same"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await merge_entities(entity_ids, TENANT_ID)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("400 Bad Request"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.MergeEntitiesRequest")
    async def test_invalid_request(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        entity_ids = ["entity1", "entity2"]
        formatted_ids = ["entities/entity1", "entities/entity2"]
        mock_request_model.return_value.entity_ids = formatted_ids
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/_same"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await merge_entities(entity_ids, TENANT_ID)
        assert result["error"]["code_key"] == "INVALID_REQUEST"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.MergeEntitiesRequest")
    async def test_server_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        entity_ids = ["entity1", "entity2"]
        formatted_ids = ["entities/entity1", "entities/entity2"]
        mock_request_model.return_value.entity_ids = formatted_ids
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = "https://reltio.api/entities/_same"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await merge_entities(entity_ids, TENANT_ID)
        assert result["error"]["code_key"] == "SERVER_ERROR"

@pytest.mark.asyncio
class TestRejectEntityMatch:
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_successful_rejection(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"status": "success"}
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert isinstance(result, dict)
        assert result["status"] == "success"
        mock_http.assert_called_once_with(
            mock_get_url.return_value,
            method='POST',
            params={"uri": f"entities/{target_id}"},
            headers=mock_headers.return_value
        )
    
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_successful_rejection_empty_response(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = None  # API returns empty response
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "Successfully rejected match" in result["message"]
    
    @patch("src.tools.entity.RejectMatchRequest", side_effect=ValueError("Invalid ID"))
    async def test_validation_error(self, _):
        result = await reject_entity_match("!invalid!", "target123", TENANT_ID)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"
    
    @patch("src.tools.entity.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_authentication_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("404 Not Found"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_entity_not_found(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("400 Bad Request"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_invalid_request(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert result["error"]["code_key"] == "INVALID_REQUEST"
    
    @patch("src.tools.entity.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    @patch("src.tools.entity.RejectMatchRequest")
    async def test_server_error(self, mock_request_model, mock_get_url, mock_headers, mock_validate, mock_http):
        source_id = "source123"
        target_id = "target456"
        mock_request_model.return_value.source_id = source_id
        mock_request_model.return_value.target_id = target_id
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_get_url.return_value = f"https://reltio.api/entities/{source_id}/_notMatch"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        result = await reject_entity_match(source_id, target_id, TENANT_ID)
        assert result["error"]["code_key"] == "SERVER_ERROR"

@pytest.mark.asyncio
class TestExportMergeTree:
    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    async def test_successful_response(self, mock_get_url, mock_headers, mock_validate, mock_http):
        mock_get_url.return_value = "https://reltio.api/entities/123ABC"
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_http.return_value = {"status": "completed"}

        result = await export_merge_tree("dummy.svr@email.com", TENANT_ID)

        assert isinstance(result, dict)
        assert result["status"] == "completed"

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.validate_connection_security", side_effect=Exception("Auth failed"))
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    async def test_authentication_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await export_merge_tree("dummy.svr@email.com", TENANT_ID)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.entity.http_request", side_effect=Exception("Internal Server Error"))
    @patch("src.tools.entity.validate_connection_security")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.get_reltio_url")
    async def test_server_error(self, mock_get_url, mock_headers, mock_validate, mock_http):
        result = await export_merge_tree("dummy.svr@email.com", TENANT_ID)
        assert result["error"]["code_key"] == "SERVER_ERROR"

@pytest.mark.asyncio
class TestUnmergeEntityByContributor:
    """Test cases for the unmerge_entity_by_contributor function."""

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.validate_connection_security")
    async def test_unmerge_entity_by_contributor_success(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test successful unmerge of a contributor entity."""
        # Setup mocks
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        
        # Mock result with 'a' (modified origin) and 'b' (spawn) entities
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_http_request.return_value = mock_result

        # Call the function
        result = await unmerge_entity_by_contributor("origin", "contributor", "test_tenant")

        # Assertions
        assert result == mock_result
        mock_validate_security.assert_called_once()
        mock_get_headers.assert_called_once()
        mock_http_request.assert_called_once()
        
        # Verify the URL and parameters are correct
        call_args, call_kwargs = mock_http_request.call_args
        assert "entities/origin/_unmerge" in call_args[0]
        assert call_kwargs["params"]["contributorURI"] == "entities/contributor"
        assert call_kwargs["method"] == "POST"

    @patch("src.tools.entity.UnmergeEntityRequest")
    async def test_unmerge_entity_by_contributor_validation_error(self, mock_request_model):
        """Test unmerge with validation error."""
        # Setup mock to raise a validation error
        mock_request_model.side_effect = ValueError("Invalid entity ID")
        
        # Call the function
        result = await unmerge_entity_by_contributor("invalid-id", "contributor", "test_tenant")

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "VALIDATION_ERROR"
        assert "Invalid entity ID" in result["error"]["message"]

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.validate_connection_security")
    async def test_unmerge_entity_by_contributor_not_found(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test unmerge with entity not found error."""
        # Setup mocks
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_http_request.side_effect = Exception("API Error: 404 Not Found")

        # Call the function
        result = await unmerge_entity_by_contributor("origin", "contributor", "test_tenant")

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"
        assert "not found" in result["error"]["message"]

@pytest.mark.asyncio
class TestUnmergeEntityTreeByContributor:
    """Test cases for the unmerge_entity_tree_by_contributor function."""

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.validate_connection_security")
    async def test_unmerge_entity_tree_by_contributor_success(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test successful tree unmerge of a contributor entity."""
        # Setup mocks
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        
        # Mock result with 'a' (modified origin) and 'b' (spawn) entities
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_http_request.return_value = mock_result

        # Call the function
        result = await unmerge_entity_tree_by_contributor("origin", "contributor", "test_tenant")

        # Assertions
        assert result == mock_result
        mock_validate_security.assert_called_once()
        mock_get_headers.assert_called_once()
        mock_http_request.assert_called_once()
        
        # Verify the URL and parameters are correct
        call_args, call_kwargs = mock_http_request.call_args
        assert "entities/origin/_treeUnmerge" in call_args[0]
        assert call_kwargs["params"]["contributorURI"] == "entities/contributor"
        assert call_kwargs["method"] == "POST"

    @patch("src.tools.entity.UnmergeEntityRequest")
    async def test_unmerge_entity_tree_by_contributor_validation_error(self, mock_request_model):
        """Test tree unmerge with validation error."""
        # Setup mock to raise a validation error
        mock_request_model.side_effect = ValueError("Invalid entity ID")
        
        # Call the function
        result = await unmerge_entity_tree_by_contributor("invalid-id", "contributor", "test_tenant")

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "VALIDATION_ERROR"
        assert "Invalid entity ID" in result["error"]["message"]

    @patch("src.tools.entity.http_request")
    @patch("src.tools.entity.get_reltio_headers")
    @patch("src.tools.entity.validate_connection_security")
    async def test_unmerge_entity_tree_by_contributor_not_found(self, mock_validate_security, mock_get_headers, mock_http_request):
        """Test tree unmerge with entity not found error."""
        # Setup mocks
        mock_get_headers.return_value = {"Authorization": "Bearer token"}
        mock_http_request.side_effect = Exception("API Error: 404 Not Found")

        # Call the function
        result = await unmerge_entity_tree_by_contributor("origin", "contributor", "test_tenant")

        # Assertions
        assert "error" in result
        assert result["error"]["code_key"] == "RESOURCE_NOT_FOUND"
        assert "not found" in result["error"]["message"]
