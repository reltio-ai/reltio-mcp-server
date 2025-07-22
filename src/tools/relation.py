import logging
import yaml
from src.env import RELTIO_TENANT
from src.util.api import get_reltio_url, http_request, create_error_response, validate_connection_security
from src.util.auth import get_reltio_headers
from src.util.models import RelationIdRequest
from src.util.activity_log import ActivityLog
from src.tools.util import simplify_reltio_attributes


# Configure logging
logger = logging.getLogger("mcp.server.reltio")


async def get_relation_details(relation_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get detailed information about a Reltio relation by ID
    
    Args:
        relation_id (str): The ID of the relation to retrieve
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the relation details
    
    Raises:
        Exception: If there's an error getting the relation details
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = RelationIdRequest(
                relation_id=relation_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_relation_details: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid relation ID format: {str(e)}"
            )
        
        # Construct URL with validated relation ID
        url = get_reltio_url(f"relations/{request.relation_id}", "api", request.tenant_id)
        
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
            relation = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check if it's a 404 error (relation not found)
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Relation with ID {request.relation_id} not found"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve relation details from Reltio API"
            )
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_relation_details_tool : Successfully fetched relation details for relation {relation_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_relation_details: {str(log_error)}")
        relation["attributes"]=simplify_reltio_attributes(relation["attributes"])
        return yaml.dump(relation, sort_keys=False)
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in get_relation_details: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while retrieving relation details"
        )
