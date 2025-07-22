import logging
import yaml
from src.env import RELTIO_TENANT
from src.util.api import (
    get_reltio_url,
    http_request, 
    create_error_response, 
    validate_connection_security
)
from src.util.auth import get_reltio_headers
from src.util.activity_log import ActivityLog

# Configure logging
logger = logging.getLogger("mcp.server.reltio")
   
async def get_business_configuration(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get business configuration for a tenant
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the business configuration
    
    Raises:
        Exception: If there's an error getting the business configuration
    """
    try:
        # Construct URL with validated tenant ID
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        
        try:
            headers = get_reltio_headers()
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        response = {}
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        
        response["uri"] = business_config.get("uri", {})
        response["description"] = business_config.get("description", {})
        response["schemaVersion"] = business_config.get("schemaVersion", {})
        response["sources"] = business_config.get("sources", {})
        return response
    
    except Exception as e:
        logger.error(f"Error in get_business_configuration: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving business configuration: {str(e)}"
        )
    
async def get_tenant_permissions_metadata(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get tenant permissions metadata
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the tenant permissions metadata
    
    Raises:
        Exception: If there's an error getting the tenant permissions metadata
    """
    try:
        # Construct URL with validated tenant ID
        url = get_reltio_url("", "permissions", tenant_id)
        
        try:
            headers = get_reltio_headers()
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Make the request with timeout
        try:
            permissions_metadata = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve tenant permissions metadata: {str(e)}"
            )
        
        try:
            await ActivityLog.execute_and_log_activity(
                    tenant_id=tenant_id,
                    description=f"get_tenant_permissions_metadata_tool : MCP server successfully fetched tenant permissions metadata"
                )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_tenant_permissions_metadata: {str(log_error)}")

        return yaml.dump(permissions_metadata,sort_keys=False)
    
    except Exception as e:
        logger.error(f"Error in get_tenant_permissions_metadata: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving tenant permissions metadata: {str(e)}"
        )

async def get_tenant_metadata(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the tenant metadata details from the business configuration for a specific tenant"""
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        response = {}
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response["uri"] = business_config.get("uri", "")
        response["description"] = business_config.get("description", "")
        response["schemaVersion"] = business_config.get("schemaVersion", "")
        response["sources"] = len(business_config.get("sources", []))
        response["label"] = business_config.get("label", "")
        response["createdTime"] = business_config.get("createdTime", "")
        response["updatedTime"] = business_config.get("updatedTime", "")
        response["createdBy"] = business_config.get("createdBy", "")
        response["updatedBy"] = business_config.get("updatedBy", "")
        response["entityTypes"] = len(business_config.get("entityTypes", []))
        response["changeRequestTypes"] = len(business_config.get("changeRequestTypes", []))
        response["relationTypes"] = len(business_config.get("relationTypes", []))
        response["interactionTypes"] = len(business_config.get("interactionTypes", []))
        response["graphTypes"] = len(business_config.get("graphTypes", []))
        response["survivorshipStrategies"] = len(business_config.get("survivorshipStrategies", []))
        response["groupingTypes"] = len(business_config.get("groupingTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_tenant_metadata_tool : MCP server successfully fetched tenant metadata for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_tenant_metadata: {str(log_error)}")
        return yaml.dump(response, sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_tenant_metadata: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving tenant metadata: {str(e)}"
        )

async def get_data_model_definition(object_type: list, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get complete details about the data model definition from the business configuration for a specific tenant"""
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        response = {}
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        if len(object_type) == 0 or "entityTypes" in object_type:
            processed_entity_types = []
            for entity_type in business_config.get("entityTypes", []):
                entity_info = {
                    "uri": entity_type.get("uri", ""),
                    "label": entity_type.get("label", ""),
                    "description": entity_type.get("description", "")
                }
                processed_entity_types.append(entity_info)
            response["entityTypes"] = processed_entity_types
        if len(object_type) == 0 or "changeRequestTypes" in object_type:
            processed_change_request_types = []
            for change_request_type in business_config.get("changeRequestTypes", []):
                change_request_info = {
                    "uri": change_request_type.get("uri", "")
                }
                processed_change_request_types.append(change_request_info)
            response["changeRequestTypes"] = processed_change_request_types
        if len(object_type) == 0 or "relationTypes" in object_type:
            processed_relation_types = []
            for relation_type in business_config.get("relationTypes", []):
                relation_info = {
                    "uri": relation_type.get("uri", ""),
                    "label": relation_type.get("label", ""),
                    "description": relation_type.get("description", "")
                }
                processed_relation_types.append(relation_info)
            response["relationTypes"] = processed_relation_types
        if len(object_type) == 0 or "interactionTypes" in object_type:
            processed_interaction_types = []
            for interaction_type in business_config.get("interactionTypes", []):
                interaction_info = {
                    "uri": interaction_type.get("uri", ""),
                    "label": interaction_type.get("label", "")
                }
                processed_interaction_types.append(interaction_info)
            response["interactionTypes"] = processed_interaction_types
        if len(object_type) == 0 or "graphTypes" in object_type:
            processed_graph_types = []
            for graph_type in business_config.get("graphTypes", []):
                graph_info = {
                    "uri": graph_type.get("uri", ""),
                    "label": graph_type.get("label", ""),
                    "relationshipTypeURIs": graph_type.get("relationshipTypeURIs", [])
                }
                processed_graph_types.append(graph_info)
            response["graphTypes"] = processed_graph_types
        if len(object_type) == 0 or "survivorshipStrategies" in object_type:
            processed_survivorship_strategies = []
            for survivorship_strategy in business_config.get("survivorshipStrategies", []):
                survivorship_info = {
                    "uri": survivorship_strategy.get("uri", ""),
                    "label": survivorship_strategy.get("label", "")
                }
                processed_survivorship_strategies.append(survivorship_info)
            response["survivorshipStrategies"] = processed_survivorship_strategies
        if len(object_type) == 0 or "groupingTypes" in object_type:
            processed_grouping_types = []
            for grouping_type in business_config.get("groupingTypes", []):
                grouping_info = {
                    "uri": grouping_type.get("uri", ""),
                    "description": grouping_type.get("description", "")
                }
                processed_grouping_types.append(grouping_info)
            response["groupingTypes"] = processed_grouping_types
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_data_model_definition_tool : MCP server successfully fetched data model definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_data_model_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_data_model_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving data model definition: {str(e)}"
        )

# Utility functions for extracting definitions from business_config

def get_entity_type_definition_util(entity_type: str, entity_types: list) -> dict:
    for e_type in entity_types:
        if e_type.get("uri", "") == entity_type:
            entity_info = {
                "uri": e_type.get("uri", ""),
                "label": e_type.get("label", ""),
                "description": e_type.get("description", ""),
                "attributes": []
            }
            attributes = e_type.get("attributes", [])
            for attr in attributes:
                attr_info = {
                    "label": attr.get("label", ""),
                    "name": attr.get("name", ""),
                    "description": attr.get("description", ""),
                    "type": attr.get("type", ""),
                    "required": attr.get("required", False),
                    "searchable": attr.get("searchable", False)
                }
                entity_info["attributes"].append(attr_info)
            return entity_info
    return {}

def get_change_request_type_definition_util(change_request_type: str, change_request_types: list) -> dict:
    for cr_type in change_request_types:
        if cr_type.get("uri", "") == change_request_type:
            change_request_info = {
                "uri": cr_type.get("uri", "")
            }
            return change_request_info
    return {}

def get_relation_type_definition_util(relation_type: str, relation_types: list) -> dict:
    for r_type in relation_types:
        if r_type.get("uri", "") == relation_type:
            relation_info = {
                "uri": r_type.get("uri", ""),
                "label": r_type.get("label", ""),
                "description": r_type.get("description", ""),
                "startObject": r_type.get("startObject", {}).get("objectTypeURI", ""),
                "endObject": r_type.get("endObject", {}).get("objectTypeURI", ""),
                "attributes": []
            }
            attributes = r_type.get("attributes", [])
            for attr in attributes:
                attr_info = {
                    "label": attr.get("label", ""),
                    "name": attr.get("name", ""),
                    "description": attr.get("description", ""),
                    "type": attr.get("type", ""),
                    "required": attr.get("required", False),
                    "searchable": attr.get("searchable", False)
                }
                relation_info["attributes"].append(attr_info)
            return relation_info
    return {}

def get_interaction_type_definition_util(interaction_type: str, interaction_types: list) -> dict:
    for i_type in interaction_types:
        if i_type.get("uri", "") == interaction_type:
            interaction_info = {
                "uri": i_type.get("uri", ""),
                "label": i_type.get("label", ""),
                "memberTypes": [],
                "attributes": []
            }
            member_types = i_type.get("memberTypes", [])
            for member_type in member_types:
                member_info = {
                    "name": member_type.get("name", "")
                }
                interaction_info["memberTypes"].append(member_info)
            attributes = i_type.get("attributes", [])
            for attr in attributes:
                attr_info = {
                    "label": attr.get("label", ""),
                    "name": attr.get("name", ""),
                    "type": attr.get("type", "")
                }
                interaction_info["attributes"].append(attr_info)
            return interaction_info
    return {}

def get_graph_type_definition_util(graph_type: str, graph_types: list) -> dict:
    for g_type in graph_types:
        if g_type.get("uri", "") == graph_type:
            graph_info = {
                "uri": g_type.get("uri", ""),
                "label": g_type.get("label", ""),
                "relationshipTypeURIs": g_type.get("relationshipTypeURIs", [])
            }
            return graph_info
    return {}

def get_grouping_type_definition_util(grouping_type: str, grouping_types: list) -> dict:
    for g_type in grouping_types:
        if g_type.get("uri", "") == grouping_type:
            grouping_info = {
                "uri": g_type.get("uri", ""),
                "description": g_type.get("description", ""),
                "source": g_type.get("source", "")
            }
            return grouping_info
    return {}

async def get_entity_type_definition(entity_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_entity_type_definition_util(entity_type, business_config.get("entityTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_entity_type_definition_tool : MCP server successfully fetched {entity_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_entity_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_entity_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving entity type definition: {str(e)}"
        )

async def get_change_request_type_definition(change_request_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_change_request_type_definition_util(change_request_type, business_config.get("changeRequestTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_change_request_type_definition_tool : MCP server successfully fetched {change_request_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_change_request_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_change_request_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving change request type definition: {str(e)}"
        )

async def get_relation_type_definition(relation_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_relation_type_definition_util(relation_type, business_config.get("relationTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_relation_type_definition_tool : MCP server successfully fetched {relation_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_relation_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_relation_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving relation type definition: {str(e)}"
        )

async def get_interaction_type_definition(interaction_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_interaction_type_definition_util(interaction_type, business_config.get("interactionTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_interaction_type_definition_tool : MCP server successfully fetched {interaction_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_interaction_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_interaction_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving interaction type definition: {str(e)}"
        )

async def get_graph_type_definition(graph_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_graph_type_definition_util(graph_type, business_config.get("graphTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_graph_type_definition_tool : MCP server successfully fetched {graph_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_graph_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_graph_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving graph type definition: {str(e)}"
        )

async def get_grouping_type_definition(grouping_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    try:
        url = get_reltio_url("configuration/_noInheritance", "api", tenant_id)
        try:
            headers = get_reltio_headers()
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        try:
            business_config = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve business configuration: {str(e)}"
            )
        response = get_grouping_type_definition_util(grouping_type, business_config.get("groupingTypes", []))
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_grouping_type_definition_tool : MCP server successfully fetched {grouping_type} definition for tenant {tenant_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_grouping_type_definition: {str(log_error)}")
        return yaml.dump(response,sort_keys=False)
    except Exception as e:
        logger.error(f"Error in get_grouping_type_definition: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving grouping type definition: {str(e)}"
        )
