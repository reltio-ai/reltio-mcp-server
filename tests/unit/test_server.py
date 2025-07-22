"""
Unit tests for the Reltio MCP Server (server.py)
"""
import pytest
from unittest.mock import patch
from unittest.mock import ANY

# Import the server module
import src.server
from src.env import RELTIO_SERVER_NAME


class TestServerInitialization:
    """Tests for server initialization and setup."""
    
    def test_server_name(self):
        """Test that the server is initialized with the correct name."""
        assert src.server.mcp.name == RELTIO_SERVER_NAME
        
    def test_logger_setup(self):
        """Test that the logger is properly configured."""
        assert src.server.logger.name == "mcp.server.reltio"


@pytest.mark.asyncio
class TestSearchEntitiesEndpoint:
    """Tests for the search_entities endpoint."""
    
    @patch('src.server.search_entities')
    async def test_search_entities_default_params(self, mock_search_entities):
        """Test search_entities with default parameters."""
        # Setup mock
        mock_search_entities.return_value = {"results": []}
        
        # Call the function
        result = await src.server.search_entities_tool(filter="filter", entity_type="entity_type", tenant_id="tenant_id", max_results=10)
        
        # Verify the tool was called with correct parameters
        mock_search_entities.assert_called_once_with(
            "filter and equals(type,'configuration/entityTypes/entity_type')", 'entity_type', 'tenant_id', 10, '', 'asc', 'uri,label', 'ovOnly', 'active', 0
        )
        assert result == {"results": []}
        
    @patch('src.server.search_entities')
    async def test_search_entities_with_params(self, mock_search_entities):
        """Test search_entities with custom parameters."""
        # Setup mock
        mock_search_entities.return_value = {"results": ["entity1"]}
        
        # Call the function
        result = await src.server.search_entities_tool(
            filter="test filter",
            entity_type="Individual",
            tenant_id="test-tenant",
            max_results=10
        )
        
        # Verify the tool was called with correct parameters
        mock_search_entities.assert_called_once_with(
            "test filter and equals(type,'configuration/entityTypes/Individual')", 'Individual', 'test-tenant', 10, '', 'asc', 'uri,label', 'ovOnly', 'active', 0
        )
        assert result == {"results": ["entity1"]}


@pytest.mark.asyncio
class TestGetEntityEndpoint:
    """Tests for the get_entity endpoint."""
    
    @patch('src.server.get_entity_details')
    async def test_get_entity(self, mock_get_entity):
        """Test get_entity function."""
        # Setup mock
        mock_get_entity.return_value = {"id": "entity_id", "name": "Test Entity"}
        
        # Call the function
        result = await src.server.get_entity_tool("entity_id", {"attributes": []}, "tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_entity.assert_called_once_with("entity_id", {"attributes": []}, "tenant_id")
        assert result == {"id": "entity_id", "name": "Test Entity"}

@pytest.mark.asyncio
class TestUpdateEntityAttributesEndpoint:
    """Tests for the update_entity_attributes endpoint."""
    
    @patch('src.server.update_entity_attributes')
    async def test_update_entity_attributes(self, mock_update_entity_attributes):
        """Test get_entity function."""
        # Setup mock
        mock_update_entity_attributes.return_value = {"id": "entity_id", "name": "Test Entity"}
        
        # Call the function
        result = await src.server.update_entity_attributes_tool(entity_id="entity_id", updates={'attributes': {'FirstName': 'John'}}, tenant_id="tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_update_entity_attributes.assert_called_once_with("entity_id", {'attributes': {'FirstName': 'John'}}, "tenant_id")
        assert result == {"id": "entity_id", "name": "Test Entity"}

@pytest.mark.asyncio
class TestGetMatchesEndpoint:
    """Tests for the get_matches endpoint."""
    
    @patch('src.server.get_entity_matches')
    async def test_get_matches(self, mock_get_entity_matches):
        """Test get_matches function."""
        # Setup mock
        mock_get_entity_matches.return_value = {"matches": []}
        
        # Call the function
        result = await src.server.get_entity_matches_tool("entity_id", "tenant_id", 10)
        
        # Verify the tool was called with correct parameters
        mock_get_entity_matches.assert_called_once_with("entity_id", "tenant_id", 10)
        assert result == {"matches": []}

@pytest.mark.asyncio
class TestGetMatcheHistoryEndpoint:
    """Tests for the get_match_history endpoint."""
    
    @patch('src.server.get_entity_match_history')
    async def test_get_match_history(self, mock_get_entity_match_history):
        """Test get_matches function."""
        # Setup mock
        mock_get_entity_match_history.return_value = {"matche_history": []}
        
        # Call the function
        result = await src.server.get_entity_match_history_tool("entity_id", "tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_entity_match_history.assert_called_once_with("entity_id", "tenant_id")
        assert result == {"matche_history": []}

@pytest.mark.asyncio
class TestGetRelationEndpoint:
    """Tests for the get_relation_details endpoint."""
    
    @patch('src.server.get_relation_details')
    async def test_get_relation_details(self, mock_get_relation_details):
        """Test get_matches function."""
        # Setup mock
        mock_get_relation_details.return_value = {"relation": []}
        
        # Call the function
        result = await src.server.get_relation_tool("relation_id", "tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_relation_details.assert_called_once_with("relation_id", "tenant_id")
        assert result == {"relation": []}


@pytest.mark.asyncio
class TestFindByMatchScoreEndpoint:
    """Tests for the find_by_match_score endpoint."""
    
    @patch('src.server.find_entities_by_match_score_tool')
    async def test_find_by_match_score(self, mock_find_entities_by_match_score_tool):
        """Test find_by_match_score function."""
        # Setup mock
        mock_find_entities_by_match_score_tool.return_value = {"matches": []}
        
        # Call the function
        result = await src.server.find_entities_by_match_score_tool(
            start_match_score=50,
            end_match_score=100,
            entity_type="Individual",
            tenant_id="tenant_id",
            max_results=10
        )
        
        # Verify the tool was called with correct parameters
        mock_find_entities_by_match_score_tool.assert_called_once_with(
            start_match_score=50,
            end_match_score=100,
            entity_type="Individual",
            tenant_id="tenant_id",
            max_results=10
        )
        assert result == {"matches": []}


@pytest.mark.asyncio
class TestFindByConfidenceEndpoint:
    """Tests for the find_by_confidence endpoint."""
    
    @patch('src.server.find_entities_by_confidence_tool')
    async def test_find_by_confidence(self, mock_find_entities_by_confidence_tool):
        """Test find_by_confidence function."""
        # Setup mock
        mock_find_entities_by_confidence_tool.return_value = {"confidence_matches": []}
        
        # Call the function
        result = await src.server.find_entities_by_confidence_tool(
            confidence_level="Low confidence", entity_type="Individual", tenant_id="tenant_id", max_results=25)
        
        # Verify the tool was called with correct parameters
        mock_find_entities_by_confidence_tool.assert_called_once_with(
            confidence_level="Low confidence",
            entity_type="Individual",
            tenant_id="tenant_id",
            max_results=25
        )
        assert result == {"confidence_matches": []}

@pytest.mark.asyncio
class TestGetTotalMatchesEndpoint:
    """Tests for the get_total_matches endpoint."""
    
    @patch('src.server.get_total_matches')
    async def test_get_total_matches(self, mock_get_total_matches):
        """Test get_total_matches function."""
        # Setup mock
        mock_get_total_matches.return_value = {"total": 1114, "min_matches": 0}
        
        # Call the function
        result = await src.server.get_total_matches_tool(0, "tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_total_matches.assert_called_once_with(0, "tenant_id")
        assert result == {"total": 1114, "min_matches": 0}

@pytest.mark.asyncio
class TestGetTotalMatchesByEntityTypeEndpoint:
    """Tests for the get_total_matches_by_entity_type endpoint."""
    
    @patch('src.server.get_total_matches_by_entity_type')
    async def test_get_total_matches_by_entity_type(self, mock_get_total_matches_by_entity_type):
        """Test get_total_matches_by_entity_type function."""
        # Setup mock
        mock_get_total_matches_by_entity_type.return_value = {
            "type_counts": {"Individual": 56, "Organization": 1058},
            "min_matches": 0
        }
        
        # Call the function
        result = await src.server.get_total_matches_by_entity_type_tool(0, "tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_total_matches_by_entity_type.assert_called_once_with(0, "tenant_id")
        assert result == {"type_counts": {"Individual": 56, "Organization": 1058}, "min_matches": 0}

@pytest.mark.asyncio
class TestMergeEntitiesEndpoint:
    """Tests for the merge_entities_tool endpoint."""
    
    @patch('src.server.merge_entities')
    async def test_merge_entities(self, mock_merge_entities):
        """Test merge_entities_tool function."""
        # Setup mock
        mock_merge_entities.return_value = {"id": "merged_entity_id", "status": "success"}
        
        # Call the function
        result = await src.server.merge_entities_tool(
            entity_ids=["entities/123abc", "entities/456def"],
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_merge_entities.assert_called_once_with(
            ["entities/123abc", "entities/456def"], "test-tenant"
        )
        assert result == {"id": "merged_entity_id", "status": "success"}
    
    @patch('src.server.merge_entities')
    async def test_merge_entities_with_plain_ids(self, mock_merge_entities):
        """Test merge_entities_tool function with plain IDs."""
        # Setup mock
        mock_merge_entities.return_value = {"id": "merged_entity_id", "status": "success"}
        
        # Call the function with plain IDs
        result = await src.server.merge_entities_tool(
            entity_ids=["123abc", "456def"],
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_merge_entities.assert_called_once_with(
            ["123abc", "456def"], "test-tenant"
        )
        assert result == {"id": "merged_entity_id", "status": "success"}

@pytest.mark.asyncio
class TestRejectEntityMatchEndpoint:
    """Tests for the reject_entity_match_tool endpoint."""
    
    @patch('src.server.reject_entity_match')
    async def test_reject_entity_match(self, mock_reject_entity_match):
        """Test reject_entity_match_tool function."""
        # Setup mock
        mock_reject_entity_match.return_value = {"success": True, "status": "rejected"}
        
        # Call the function
        result = await src.server.reject_entity_match_tool(
            source_id="entity1",
            target_id="entity2",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_reject_entity_match.assert_called_once_with(
            "entity1", "entity2", "test-tenant"
        )
        assert result == {"success": True, "status": "rejected"}
    
    @patch('src.server.reject_entity_match')
    async def test_reject_entity_match_with_entity_prefix(self, mock_reject_entity_match):
        """Test reject_entity_match_tool function with entities/ prefix."""
        # Setup mock
        mock_reject_entity_match.return_value = {"success": True, "status": "rejected"}
        
        # Call the function with entity prefix
        result = await src.server.reject_entity_match_tool(
            source_id="entities/entity1",
            target_id="entities/entity2",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_reject_entity_match.assert_called_once_with(
            "entities/entity1", "entities/entity2", "test-tenant"
        )
        assert result == {"success": True, "status": "rejected"}

@pytest.mark.asyncio
class TestExportMergeTreeEndpoint:
    """Tests for the export_merge_tree endpoint."""
    
    @patch('src.server.export_merge_tree')
    async def test_export_merge_tree(self, mock_export_merge_tree):
        """Test export_merge_tree function."""
        # Setup mock
        mock_export_merge_tree.return_value = {"success": True, "status": "completed"}
        
        # Call the function
        result = await src.server.export_merge_tree_tool(email_id="dummy.svr@email.com", tenant_id="tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_export_merge_tree.assert_called_once_with("dummy.svr@email.com", "tenant_id")
        assert result == {"success": True, "status": "completed"}

@pytest.mark.asyncio
class TestBusinessConfigEndpoint:
    """Tests for the get_business_configuration endpoint."""
    
    @patch('src.server.get_business_configuration')
    async def test_get_business_configuration(self, mock_get_business_configuration):
        """Test get_business_configuration function."""
        # Setup mock
        mock_get_business_configuration.return_value = {"success": True, "status": "completed"}
        
        # Call the function
        result = await src.server.get_business_configuration_tool(tenant_id="tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_business_configuration.assert_called_once_with("tenant_id")
        assert result == {"success": True, "status": "completed"}

@pytest.mark.asyncio
class TestTenantPermissionMetadataEndpoint:
    """Tests for the get_tenant_permissions_metadata endpoint."""
    
    @patch('src.server.get_tenant_permissions_metadata')
    async def test_get_tenant_permissions_metadata(self, mock_get_tenant_permissions_metadata):
        """Test get_tenant_permissions_metadata function."""
        # Setup mock
        mock_get_tenant_permissions_metadata.return_value = {"success": True, "status": "completed"}
        
        # Call the function
        result = await src.server.get_tenant_permissions_metadata_tool(tenant_id="tenant_id")
        
        # Verify the tool was called with correct parameters
        mock_get_tenant_permissions_metadata.assert_called_once_with("tenant_id")
        assert result == {"success": True, "status": "completed"}

@pytest.mark.asyncio
class TestCapabilitiesEndpoint:
    """Tests for the capabilities endpoint."""
    
    @patch('src.server.list_capabilities')
    async def test_capabilities(self, mock_list_capabilities):
        """Test capabilities function."""
        # Setup mock
        mock_list_capabilities.return_value = {"tools": [], "resources": []}
        
        # Call the function
        result = await src.server.capabilities_tool()
        
        # Verify the tool was called with correct parameters
        mock_list_capabilities.assert_called_once_with()
        assert result == {"tools": [], "resources": []}

@pytest.mark.asyncio
async def test_get_merge_activities_tool():
    """Test get_merge_activities_tool wrapper function."""
    # Add the mock to patch the implementation function
    with patch("src.server.get_merge_activities") as mock_get_merge_activities:
        # Setup the mock to return a sample response
        mock_response = {
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
                }
            ],
            "total": 1
        }
        mock_get_merge_activities.return_value = mock_response
        
        # Call the tool function
        result = await src.server.get_merge_activities_tool(
            timestamp_gt=1744191663000,
            event_types=["ENTITIES_MERGED_MANUALLY"],
            entity_type="Individual",
            tenant_id="test_tenant"
        )
        
        # Assert that the implementation function was called with the correct parameters
        mock_get_merge_activities.assert_called_once_with(
            timestamp_gt=1744191663000,
            event_types=["ENTITIES_MERGED_MANUALLY"],
            entity_type="Individual",
            tenant_id="test_tenant",
            timestamp_lt=None,
            user=None,
            offset=0,
            max_results=100
        )
        
        # Assert that the tool function returns the response from the implementation function
        assert result == mock_response

@pytest.mark.asyncio
class TestUnmergeEntityByContributorEndpoint:
    """Tests for the unmerge_entity_by_contributor_tool endpoint."""
    
    @patch('src.server.unmerge_entity_by_contributor')
    async def test_unmerge_entity_by_contributor(self, mock_unmerge_entity_by_contributor):
        """Test unmerge_entity_by_contributor_tool function."""
        # Setup mock
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_unmerge_entity_by_contributor.return_value = mock_result
        
        # Call the function
        result = await src.server.unmerge_entity_by_contributor_tool(
            origin_entity_id="origin",
            contributor_entity_id="contributor",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_unmerge_entity_by_contributor.assert_called_once_with(
            "origin", "contributor", "test-tenant"
        )
        assert result == mock_result
    
    @patch('src.server.unmerge_entity_by_contributor')
    async def test_unmerge_entity_by_contributor_with_entity_prefix(self, mock_unmerge_entity_by_contributor):
        """Test unmerge_entity_by_contributor_tool function with entities/ prefix."""
        # Setup mock
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_unmerge_entity_by_contributor.return_value = mock_result
        
        # Call the function with entity prefix
        result = await src.server.unmerge_entity_by_contributor_tool(
            origin_entity_id="entities/origin",
            contributor_entity_id="entities/contributor",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_unmerge_entity_by_contributor.assert_called_once_with(
            "entities/origin", "entities/contributor", "test-tenant"
        )
        assert result == mock_result

@pytest.mark.asyncio
class TestUnmergeEntityTreeByContributorEndpoint:
    """Tests for the unmerge_entity_tree_by_contributor_tool endpoint."""
    
    @patch('src.server.unmerge_entity_tree_by_contributor')
    async def test_unmerge_entity_tree_by_contributor(self, mock_unmerge_entity_tree_by_contributor):
        """Test unmerge_entity_tree_by_contributor_tool function."""
        # Setup mock
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_unmerge_entity_tree_by_contributor.return_value = mock_result
        
        # Call the function
        result = await src.server.unmerge_entity_tree_by_contributor_tool(
            origin_entity_id="origin",
            contributor_entity_id="contributor",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_unmerge_entity_tree_by_contributor.assert_called_once_with(
            "origin", "contributor", "test-tenant"
        )
        assert result == mock_result
    
    @patch('src.server.unmerge_entity_tree_by_contributor')
    async def test_unmerge_entity_tree_by_contributor_with_entity_prefix(self, mock_unmerge_entity_tree_by_contributor):
        """Test unmerge_entity_tree_by_contributor_tool function with entities/ prefix."""
        # Setup mock
        mock_result = {
            "a": {"uri": "entities/origin", "attributes": {}},
            "b": {"uri": "entities/contributor", "attributes": {}}
        }
        mock_unmerge_entity_tree_by_contributor.return_value = mock_result
        
        # Call the function with entity prefix
        result = await src.server.unmerge_entity_tree_by_contributor_tool(
            origin_entity_id="entities/origin",
            contributor_entity_id="entities/contributor",
            tenant_id="test-tenant"
        )
        
        # Verify the tool was called with correct parameters
        mock_unmerge_entity_tree_by_contributor.assert_called_once_with(
            "entities/origin", "entities/contributor", "test-tenant"
        )
        assert result == mock_result
