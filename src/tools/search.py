import logging
import yaml
from src.env import RELTIO_TENANT
from src.util.api import get_reltio_url, http_request, create_error_response, validate_connection_security
from src.util.auth import get_reltio_headers
from src.util.models import EntitySearchRequest
from src.util.activity_log import ActivityLog
from src.tools.util import simplify_reltio_attributes

# Configure logging
logger = logging.getLogger("mcp.server.reltio")


async def search_entities(filter: str = "", entity_type: str = "",
                              tenant_id: str = RELTIO_TENANT, max_results: int = 10,
                              sort: str = "", order: str = "asc",
                              select: str = "uri,label",
                              options: str = "ovOnly",
                              activeness: str = "active",
                              offset: int = 0) -> dict:
    """Search for entities matching the filter criteria
    
    Args:
        filter (str): Enables entities filtering by a condition. Format for filter query parameter: filter=({Condition Type}[AND/OR {Condition Type}]*).
        entity_type (str): Entity type to filter by (e.g., 'Individual', 'Organization')
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Defaults to 10.
        sort (str): Attribute name to sort by.
        order (str): Sort order ('asc' or 'desc'). Defaults to 'asc'.
        select (str): Comma-separated list of fields to select in the response.
        options (str): Options for the search query.
        activeness (str): Activeness filter for entities.
        offset (int): Starting index for paginated results. Use 0 for the first page, 10 for the second, etc.
    
    Returns:
        A dictionary containing the search results
    
    Raises:
        Exception: If there's an error executing the search
    """
    try:
        # Validate and sanitize inputs using Pydantic model
        try:
            search_request = EntitySearchRequest(
                filter=filter,
                entity_type=entity_type,
                tenant_id=tenant_id,
                max_results=min(max_results, 10),
                sort=sort,
                order=order,
                select=select,
                options=options,
                activeness=activeness,
                offset=offset
            )
        except ValueError as e:
            logger.warning(f"Validation error in search_entities_tool: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid input parameters: {str(e)}"
            )
        
        # Special URL construction specifically for search endpoint
        url = get_reltio_url("entities/_search", "api", search_request.tenant_id)
        
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
        
        # Build the payload
        payload = {
            "filter": search_request.filter,
            "select": search_request.select,
            "max": min(search_request.max_results, 10),
            "offset": search_request.offset,
            "scoreEnabled": False,
            "options": search_request.options,
            "activeness": search_request.activeness
        }

        if search_request.sort:
            payload["sort"] = search_request.sort
            payload["order"] = search_request.order
        
        # Make the request with timeout
        try:
            result = http_request(url, method='POST', headers=headers, data=payload)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve search results from Reltio API"
            )

        try:
            entity_ids = [entity.get("uri", "") for entity in result]
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"search_entities_tool : Successfully searched for entities: {entity_id_label_pairs} with entity_type {entity_type}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for search_entities_tool: {str(log_error)}")
        
        filtered_result=[]
        select_fields = [field for field in select.split(',') if field != "uri"]
        for entity in result:
            entity_dict = {}
            for field in select_fields:
                if field.startswith("attributes"):
                    entity_dict["attributes"] = simplify_reltio_attributes(entity["attributes"])
                else:
                    entity_dict[field] = entity[field]
            if entity_dict == {}:
                filtered_result.append(entity["uri"])
            else:
                filtered_result.append({entity["uri"]: entity_dict})
        return yaml.dump(filtered_result, sort_keys=False)
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in search_entities_tool: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while processing your request"
        )
