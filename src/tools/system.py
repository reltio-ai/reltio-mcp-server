import logging

from src.env import RELTIO_SERVER_NAME
from src.util.api import create_error_response

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

async def list_capabilities() -> dict:
    """List all capabilities (resources, tools, and prompts) available in this server
    
    Returns:
        A dictionary containing information about available server capabilities
    
    Raises:
        Exception: If there's an error getting the server capabilities
    """
    try:
        # Build capabilities information
        capabilities = {
            "server_name": RELTIO_SERVER_NAME,
            "tools": [
                {
                    "name": "search_entities_tool",
                    "description": "Search for entities with advanced filtering",
                    "parameters": ["filter", "entity_type", "tenant_id", "max_results", "sort", "order", "select", "options", "activeness", "offset" ]
                },
                {
                    "name": "get_entity_tool",
                    "description": "Get detailed information about a Reltio entity by ID",
                    "parameters": ["entity_id", "tenant_id"]
                },
                {
                    "name": "update_entity_attributes_tool",
                    "description": "Update specific attributes of an entity in Reltio.",
                    "parameters": ["entity_id", "updates", "tenant_id"]
                },
                {
                    "name": "get_entity_matches_tool",
                    "description": "Find potential matches for a specific entity",
                    "parameters": ["entity_id", "tenant_id", "max_results"]
                },
                {
                    "name": "get_entity_match_history_tool",
                    "description": "Find the match history for a specific entity",
                    "parameters": ["entity_id", "tenant_id"]
                },
                {
                    "name": "get_relation_tool",
                    "description": "Get detailed information about a Reltio relation by ID",
                    "parameters": ["relation_id", "tenant_id"]
                },
                {
                    "name": "find_entities_by_match_score_tool",
                    "description": "Find all potential matches by match score range",
                    "parameters": ["start_match_score", "end_match_score", "entity_type", "tenant_id", "max_results", "offset"]
                },
                {
                    "name": "find_entities_by_confidence_tool",
                    "description": "Find all potential matches by confidence level",
                    "parameters": ["confidence_level", "entity_type", "tenant_id", "max_results", "offset"]
                },
                {
                    "name": "get_total_matches_tool",
                    "description": "Get the total count of potential matches in the tenant",
                    "parameters": ["min_matches", "tenant_id"]
                },
                {
                    "name": "get_total_matches_by_entity_type_tool",
                    "description": "Get the facet counts of potential matches by entity type",
                    "parameters": ["min_matches", "tenant_id"]
                },
                {
                    "name": "merge_entities_tool",
                    "description": "Merge multiple entities in Reltio",
                    "parameters": ["entity_ids", "tenant_id"]
                },
                {
                    "name": "reject_entity_match_tool",
                    "description": "Mark an entity as not a match (reject the potential duplicate)",
                    "parameters": ["source_id", "target_id", "tenant_id"]
                },
                {
                    "name": "unmerge_entity_by_contributor_tool",
                    "description": "Unmerge a contributor entity from a merged entity, keeping profiles merged beneath it intact",
                    "parameters": ["origin_entity_id", "contributor_entity_id", "tenant_id"]
                },
                {
                    "name": "unmerge_entity_tree_by_contributor_tool",
                    "description": "Unmerge a contributor entity and all profiles merged beneath it from a merged entity",
                    "parameters": ["origin_entity_id", "contributor_entity_id", "tenant_id"]
                },
                {
                    "name": "export_merge_tree_tool",
                    "description": "Export the merge tree for all entities in a specific tenant",
                    "parameters": ["email_id", "tenant_id"]
                },
                {
                    "name": "get_business_configuration_tool",
                    "description": "Get the business configuration for a specific tenant",
                    "parameters": ["tenant_id"]
                },
                {
                    "name": "get_tenant_permissions_metadata_tool",
                    "description": "Get the permissions and security metadata for a specific tenant",
                    "parameters": ["tenant_id"]
                },
                {
                    "name": "get_merge_activities_tool",
                    "description": "Retrieve activity events related to entity merges with flexible filtering options",
                    "parameters": ["timestamp_gt", "event_types", "timestamp_lt", "entity_type", "user", "tenant_id", "offset", "max_results"]
                },
                {
                    "name": "get_tenant_metadata_tool",
                    "description": "Get the tenant metadata details from the business configuration for a specific tenant",
                    "parameters": ["tenant_id"]
                },
                {
                    "name": "get_data_model_definition_tool",
                    "description": "Get complete details about the data model definition from the business configuration for a specific tenant",
                    "parameters": ["object_type", "tenant_id"]
                },
                {
                    "name": "get_entity_type_definition_tool",
                    "description": "Get the entity type definition for a specified entity type from the business configuration of a specific tenant",
                    "parameters": ["entity_type", "tenant_id"]
                },
                {
                    "name": "get_change_request_type_definition_tool",
                    "description": "Get the change request type definition for a specified change request type from the business configuration of a specific tenant",
                    "parameters": ["change_request_type", "tenant_id"]
                },
                {
                    "name": "get_relation_type_definition_tool",
                    "description": "Get the relation type definition for a specified relation type from the business configuration of a specific tenant",
                    "parameters": ["relation_type", "tenant_id"]
                },
                {
                    "name": "get_interaction_type_definition_tool",
                    "description": "Get the interaction type definition for a specified interaction type from the business configuration of a specific tenant",
                    "parameters": ["interaction_type", "tenant_id"]
                },
                {
                    "name": "get_graph_type_definition_tool",
                    "description": "Get the graph type definition for a specified graph type from the business configuration of a specific tenant",
                    "parameters": ["graph_type", "tenant_id"]
                },
                {
                    "name": "get_grouping_type_definition_tool",
                    "description": "Get the grouping type definition for a specified grouping type from the business configuration of a specific tenant",
                    "parameters": ["grouping_type", "tenant_id"]
                },
                {
                    "name": "capabilities_tool",
                    "description": "Display this help information",
                    "parameters": []
                }
            ],
            "prompts": [
                {
                    "name": "duplicate_review",
                    "description": "Helps review potential duplicates for an entity"
                }
            ],
            "example_usage": [
                "search_entities_tool(filter=\"containsWordStartingWith(attributes,'John')\")",
                "search_entities_tool(filter=\"equals(type,'configuration/entityTypes/Individual')\")",
                "get_entity_tool(entity_id='118C6Ujm')",
                "update_entity_attributes_tool(entity_id='118C6Ujm', updates=[{'type': 'UPDATE_ATTRIBUTE', 'uri': 'entities/118C6Ujm/attributes/FirstName/3Z3Tq6BBE', 'newValue': [{'value': 'John'}]}])",
                "get_entity_matches_tool(entity_id='118C6Ujm')",
                "get_entity_match_history_tool(entity_id='118C6Ujm')",
                "get_relation_tool(relation_id='relation_id')",
                "find_matches_by_match_score_tool(start_match_score=50, end_match_score=100, entity_type='Individual', tenant_id='tenant_id', max_results=10)",
                "find_matches_by_confidence_tool(confidence_level='High confidence', entity_type='Individual', tenant_id='tenant_id', max_results=10)",
                "get_total_matches_tool(min_matches=0, tenant_id='tenant_id')",
                "get_total_matches_by_entity_type_tool(min_matches=0, tenant_id='tenant_id')",
                "merge_entities_tool(entity_ids=['entities/123abc', 'entities/456def'], tenant_id='tenant_id')",
                "reject_entity_match_tool(source_id='123abc', target_id='456def', tenant_id='tenant_id')",
                "unmerge_entity_by_contributor_tool(origin_entity_id='123abc', contributor_entity_id='456def', tenant_id='tenant_id')",
                "unmerge_entity_tree_by_contributor_tool(origin_entity_id='123abc', contributor_entity_id='456def', tenant_id='tenant_id')",
                "export_merge_tree_tool(email_id='dummy.svr@email.com', tenant_id='tenant_id')",
                "get_business_configuration_tool(tenant_id='tenant_id')",
                "get_tenant_permissions_metadata_tool(tenant_id='tenant_id')",
                "get_merge_activities_tool(timestamp_gt=1744191663000, event_types=['ENTITIES_MERGED_MANUALLY'], entity_type='Individual')",
                "get_tenant_metadata_tool(tenant_id='tenant_id')",
                "get_data_model_definition_tool(object_type=['entityTypes'], tenant_id='tenant_id')",
                "get_entity_type_definition_tool(entity_type='configuration/entityTypes/Organization', tenant_id='tenant_id')",
                "get_change_request_type_definition_tool(change_request_type='configuration/changeRequestTypes/default', tenant_id='tenant_id')",
                "get_relation_type_definition_tool(relation_type='configuration/relationTypes/OrganizationIndividual', tenant_id='tenant_id')",
                "get_interaction_type_definition_tool(interaction_type='configuration/interactionTypes/PurchaseOrder', tenant_id='tenant_id')",
                "get_graph_type_definition_tool(graph_type='configuration/graphTypes/Hierarchy', tenant_id='tenant_id')",
                "get_grouping_type_definition_tool(grouping_type='configuration/groupingTypes/Household', tenant_id='tenant_id')",
            ]
        }
        
        return capabilities
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in list_capabilities: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while listing capabilities"
        )
