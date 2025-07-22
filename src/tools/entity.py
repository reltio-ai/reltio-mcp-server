import logging
from typing import List, Dict, Any, Optional
import yaml
from src.constants import MAX_RESULTS_LIMIT
from src.env import RELTIO_TENANT
from src.util.api import get_reltio_url, get_reltio_export_job_url, http_request, create_error_response, validate_connection_security
from src.util.auth import get_reltio_headers
from src.util.exceptions import SecurityError
from src.util.models import EntityIdRequest, UpdateEntityAttributesRequest, MergeEntitiesRequest, RejectMatchRequest, UnmergeEntityRequest
from src.util.activity_log import ActivityLog
from src.tools.util import simplify_reltio_attributes, slim_crosswalks, format_entity_matches

# Configure logging
logger = logging.getLogger("mcp.server.reltio")
   

def filter_entity(entity: Dict[str, Any], filter_field: Optional[Dict[str, List[str]]]) -> Dict[str, Any]:
    if filter_field is None:
        return entity

    def is_valid(value: Any) -> bool:
        return value is not None and not (isinstance(value, (str, list, dict, set)) and len(value) == 0)

    filtered_entity = {}
    for field, subfields in filter_field.items():
        if field not in entity:
            continue
        value = entity[field]
        if not is_valid(value):
            continue

        # Handle subfield filtering for nested fields like "attributes"
        if isinstance(value, dict) and subfields:
            subvalue = {
                k: v for k, v in value.items()
                if k in subfields and is_valid(v)
            }
            if subvalue:
                filtered_entity[field] = subvalue
        elif isinstance(value, dict) and not subfields:
            # Include whole dict if subfields list is empty
            filtered_subdict = {k: v for k, v in value.items() if is_valid(v)}
            if filtered_subdict:
                filtered_entity[field] = filtered_subdict
        else:
            # For non-dict values (e.g., lists, strings, booleans)
            filtered_entity[field] = value
    return filtered_entity

async def get_entity_details(entity_id: str, filter_field: Dict[str, List[str]] = None, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get detailed information about a Reltio entity by ID
    
    Args:
        entity_id (str): The ID of the entity to retrieve
        filter_field (Dict[str, List[str]]): Optional dictionary to filter specific fields in the entity response
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the entity details
    
    Raises:
        Exception: If there's an error getting the entity details
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = EntityIdRequest(
                entity_id=entity_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_entity_details: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
        
        # Construct URL with validated entity ID
        url = get_reltio_url(f"entities/{request.entity_id}", "api", request.tenant_id)
        
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
            entity = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check if it's a 404 error (entity not found)
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Entity with ID {request.entity_id} not found"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve entity details from Reltio API"
            )
        
        # Try to log activity for success
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_entity_details_tool : Successfully fetched entity details for entity: {entity_id}, label: {entity.get('label', '')} with filter {filter_field}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_entity_details: {str(log_error)}")
        
        filter_entity_data=filter_entity(entity, filter_field) if filter_field else entity
        result={"attributes":simplify_reltio_attributes(filter_entity_data.get("attributes",{}))}
        if "crosswalks" in filter_entity_data:
            result["crosswalks"]=slim_crosswalks(filter_entity_data["crosswalks"])

        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in get_entity_details: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while retrieving entity details"
        )

async def update_entity_attributes(entity_id: str, updates: List[Dict[str, Any]], tenant_id: str = RELTIO_TENANT) -> dict:
    """Update specific attributes of an entity in Reltio
    
    Args:
        entity_id (str): Entity ID to update
        updates (List[Dict[str, Any]]): List of update operations as per Reltio API spec
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the API response
    
    Raises:
        Exception: If there's an error during the update
    """
    try:
        # Validate request
        try:
            request = UpdateEntityAttributesRequest(
                entity_id=entity_id,
                updates=updates,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in update_entity_attributes: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request format: {str(e)}"
            )

        url = get_reltio_url(f"entities/{request.entity_id}/_update", "api", request.tenant_id)

        try:
            headers = get_reltio_headers()
            headers["Content-Type"] = "application/json"
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate or security requirements not met"
            )

        try:
            result = http_request(url, method="POST", headers=headers, data=request.updates)
        except Exception as e:
            logger.error(f"API request error in update_entity_attributes: {str(e)}")
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Entity with ID {request.entity_id} not found"
                )
            return create_error_response(
                "SERVER_ERROR",
                "Failed to update entity attributes in Reltio API"
            )
        
        # Try to log activity for success
        try:
            entity_label = result.get('label', '') if isinstance(result, dict) else ''
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"update_entity_attributes_tool : Successfully updated entity: {entity_id}, label: {entity_label} with updates {updates}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for update_entity_attributes: {str(log_error)}")

        return yaml.dump(result, sort_keys=False)
    except Exception as e:
        logger.error(f"Unexpected error in update_entity_attributes: {str(e)}")
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while updating entity attributes"
        )

async def get_entity_matches(entity_id: str, tenant_id: str = RELTIO_TENANT, max_results: int = 25) -> dict:
    """Find potential matches for a specific entity with detailed comparisons
    
    Args:
        entity_id (str): Entity ID to find matches for
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Default to 25
    
    Returns:
        A dictionary containing the source entity and potential matches
    
    Raises:
        Exception: If there's an error getting the potential matches for an entity
    """   
    try:
        # Validate inputs using Pydantic model
        try:
            request = EntityIdRequest(
                entity_id=entity_id,
                tenant_id=tenant_id
            )
            
            # Validate max_results
            if max_results < 1:
                max_results = 1
            elif max_results > MAX_RESULTS_LIMIT:
                max_results = MAX_RESULTS_LIMIT
                logger.info(f"Max results limited to {MAX_RESULTS_LIMIT} for entity matches")
                
        except ValueError as e:
            logger.warning(f"Validation error in get_entity_matches: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
        
        try:
            headers = get_reltio_headers()
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Use the _transitiveMatches endpoint for a specific entity
        url = get_reltio_url(f"entities/{request.entity_id}/_transitiveMatches", "api", request.tenant_id)
        
        # Validate connection security
        try:
            validate_connection_security(url, headers)
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}")
            return create_error_response(
                "SECURITY_ERROR",
                "Security requirements not met"
            )
        
        params = {
            "deep": 1,
            "markMatchedValues": "true",
            "sort": "score",
            "order": "desc",
            "activeness": "active",
            "limit": max_results
        }
        
        # Make the request with timeout
        try:
            matches_result = http_request(url, headers=headers, params=params)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check if it's a 404 error (entity not found)
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Entity with ID {request.entity_id} not found"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve matches from Reltio API"
            )
        
        # Check if we found any matches
        if not matches_result or len(matches_result) == 0:
            return {
                "message": f"No potential matches found for entity {request.entity_id}.",
                "matches": []
            }
        
        # Get the source entity
        source_url = get_reltio_url(f"entities/{request.entity_id}", "api", request.tenant_id)
        
        try:
            source_entity = http_request(source_url, headers=headers)
        except Exception as e:
            logger.error(f"Error retrieving source entity: {str(e)}")
            
            # We still have the matches, so return those with an error message about the source
            return {
                "message": f"Found matches but could not retrieve source entity details: {str(e)}",
                "matches": matches_result
            }
        
        # Combine results
        result = {
            "source_entity": request.entity_id,
            "matches": format_entity_matches(matches_result)
        }
        
        # Try to log activity for success
        try:
            source_entity_label = source_entity.get('label', '') if isinstance(source_entity, dict) else ''
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_entity_matches_tool : Successfully fetched potential matches for entity: {entity_id}, label: {source_entity_label}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_entity_matches: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in get_entity_matches: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while retrieving entity matches"
        )

async def get_entity_match_history(entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Find the match history for a specific entity
    
    Args:
        entity_id (str): Entity ID to find matches for
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the source entity and match history for that entity
    
    Raises:
        Exception: If there's an error getting the match history for an entity
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = EntityIdRequest(
                entity_id=entity_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_entity_match_history: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
        
        try:
            headers = get_reltio_headers()
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Use the _crosswalkTree endpoint for a specific entity
        url = get_reltio_url(f"entities/{request.entity_id}/_crosswalkTree", "api", request.tenant_id)
        
        # Validate connection security
        try:
            validate_connection_security(url, headers)
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}")
            return create_error_response(
                "SECURITY_ERROR",
                "Security requirements not met"
            )
        
        # Make the request with timeout
        try:
            match_history = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check if it's a 404 error (entity not found)
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Entity with ID {request.entity_id} not found"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve match history from Reltio API"
            )
        
        # Check if we found any match history
        if not match_history or len(match_history) == 0:
             # Try to log activity for no results
            try:
                await ActivityLog.execute_and_log_activity(
                    tenant_id=tenant_id,
                    description=f"get_entity_match_history_tool : No match history found for entity {request.entity_id}"
                )
            except Exception as log_error:
                logger.error(f"Activity logging failed for get_entity_match_history (no results): {str(log_error)}")
            
            return {
                "message": f"No match history found for entity {request.entity_id}.",
                "match_history": []
            }
        
        # Get the source entity
        source_url = get_reltio_url(f"entities/{request.entity_id}", "api", request.tenant_id)
        
        try:
            source_entity = http_request(source_url, headers=headers)
        except Exception as e:
            logger.error(f"Error retrieving source entity: {str(e)}")
            
            # We still have the match history, so return those with an error message about the source
            return {
                "message": f"Found match history but could not retrieve source entity details: {str(e)}",
                "match_history": match_history
            }
        
        # Try to log activity for success
        try:
            crosswalk_uris = []
            for cross_walk in match_history.get("crosswalks", []):
                crosswalk_uris.append(cross_walk.get("uri", ""))
            source_entity_label = source_entity.get('label', '') if isinstance(source_entity, dict) else ''
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_entity_match_history_tool : Successfully fetched match history for entity: {entity_id}, label: {source_entity_label}, crosswalk URIs: {crosswalk_uris}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_entity_match_history: {str(log_error)}")

        return yaml.dump(match_history, sort_keys=False)
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in get_entity_match_history: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while retrieving entity match history"
        )

async def merge_entities(entity_ids: List[str], tenant_id: str = RELTIO_TENANT) -> dict:
    """Merge two Reltio entities into one
    
    Args:
        entity_ids (List[str]): List of two entity IDs to merge
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the merge operation
    
    Raises:
        Exception: If there's an error merging the entities
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = MergeEntitiesRequest(
                entity_ids=entity_ids,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in merge_entities: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity IDs: {str(e)}"
            )
        
        # Construct URL with validated entity IDs
        url = get_reltio_url(f"entities/_same", "api", request.tenant_id)
        
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
        
        # Prepare the payload for merging entities
        payload = request.entity_ids
        
        # Make the POST request
        try:
            merge_result = http_request(
                url, 
                method='POST',
                data=payload,
                headers=headers
            )
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"One or more entities not found"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid merge request: {str(e)}"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to merge entities"
            )
        try:
            entity_ids_str = ", ".join(entity_ids)
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"merge_entities_tool : Successfully merged entities {entity_ids_str}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for merge_entities: {str(log_error)}")

        return merge_result
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in merge_entities: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while merging entities"
        )

async def reject_entity_match(source_id: str, target_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Reject a potential match between two Reltio entities
    
    Args:
        source_id (str): The ID of the source entity
        target_id (str): The ID of the target entity to reject as a match
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the reject operation
    
    Raises:
        Exception: If there's an error rejecting the match
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = RejectMatchRequest(
                source_id=source_id,
                target_id=target_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in reject_entity_match: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
        
        # Construct URL with validated entity IDs
        base_url = get_reltio_url(f"entities/{request.source_id}/_notMatch", "api", request.tenant_id)
        
        # Add the target entity URI as a query parameter
        params = {
            "uri": f"entities/{request.target_id}"
        }
        
        try:
            headers = get_reltio_headers()
            
            # Validate connection security
            validate_connection_security(base_url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Make the POST request with URL parameters
        try:
            reject_result = http_request(
                base_url, 
                method='POST',
                params=params,
                headers=headers
            )
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"One or more entities not found"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid reject match request: {str(e)}"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to reject entity match"
            )
        
        # If we reach here, the operation was successful
        # The API might not return any content, so create a meaningful response
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"reject_entity_match_tool : Successfully rejected match between entities {request.source_id} and {request.target_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for reject_entity_match: {str(log_error)}")

        if not reject_result:
            return {
                "success": True,
                "message": f"Successfully rejected match between entities {request.source_id} and {request.target_id}"
            }
        
        return reject_result
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in reject_entity_match: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while rejecting entity match"
        )

async def export_merge_tree(email_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Export the merge tree for all entities in a specific tenant.

    Args:
        email_id (str): This parameter indicates the valid email address to which the notification is sent after the export is completed.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the scheduled export job ID and status
    
    Raises:
        Exception: If there's an error exporting the merge tree
    """
    try:
        url = get_reltio_export_job_url(f"entities/_crosswalksTree", tenant_id)

        try:
            headers = get_reltio_headers()
            headers["Content-Type"] = "application/json"
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate or security requirements not met"
            )

        payload = {
            "outputAsJsonArray": True
        }
        params = {
            "email": email_id
        }
        try:
            result = http_request(url, method="POST", headers=headers, data=payload, params=params)
        except Exception as e:
            logger.error(f"API request error in export_merge_tree: {str(e)}")
            return create_error_response(
                "SERVER_ERROR",
                "Failed to schedule export merge tree job"
            )
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"export_merge_tree_tool : {str(result)}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for export_merge_tree: {str(log_error)}")

        return result
    except Exception as e:
        logger.error(f"Unexpected error in export_merge_tree: {str(e)}")
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while Scheduling the export merge tree job"
        )

async def unmerge_entity_by_contributor(origin_entity_id: str, contributor_entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Unmerge a contributor entity from a merged entity, keeping any profiles merged beneath it intact.
    
    Args:
        origin_entity_id (str): The ID of the origin entity (the merged entity)
        contributor_entity_id (str): The ID of the contributor entity to unmerge from the origin entity
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the unmerge operation with 'a' (modified origin) and 'b' (spawn) entities
    
    Raises:
        Exception: If there's an error during the unmerge operation
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = UnmergeEntityRequest(
                origin_entity_id=origin_entity_id,
                contributor_entity_id=contributor_entity_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in unmerge_entity_by_contributor: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
            
        # Construct URL with validated entity IDs
        url = get_reltio_url(f"entities/{request.origin_entity_id}/_unmerge", "api", request.tenant_id)
        
        # Add the contributor entity URI as a query parameter
        params = {
            "contributorURI": f"entities/{request.contributor_entity_id}"
        }
        
        try:
            headers = get_reltio_headers()
            headers["Content-Type"] = "application/json"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Make the POST request with URL parameters
        try:
            unmerge_result = http_request(
                url, 
                method='POST',
                params=params,
                headers=headers
            )
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"One or more entities not found"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid unmerge request: {str(e)}"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to unmerge entity"
            )
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"unmerge_entity_by_contributor_tool : Successfully unmerged origin entity {request.origin_entity_id} by contributor entity {request.contributor_entity_id}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for unmerge_entity_by_contributor: {str(log_error)}")

        return unmerge_result
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in unmerge_entity_by_contributor: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while unmerging entity"
        )

async def unmerge_entity_tree_by_contributor(origin_entity_id: str, contributor_entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Unmerge a contributor entity and all profiles merged beneath it from a merged entity.
    
    Args:
        origin_entity_id (str): The ID of the origin entity (the merged entity)
        contributor_entity_id (str): The ID of the contributor entity to unmerge from the origin entity
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the unmerge operation with 'a' (modified origin) and 'b' (spawn) entities
    
    Raises:
        Exception: If there's an error during the unmerge operation
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = UnmergeEntityRequest(
                origin_entity_id=origin_entity_id,
                contributor_entity_id=contributor_entity_id,
                tenant_id=tenant_id
            )
        except ValueError as e:
            logger.warning(f"Validation error in unmerge_entity_tree_by_contributor: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid entity ID format: {str(e)}"
            )
            
        # Construct URL with validated entity IDs
        url = get_reltio_url(f"entities/{request.origin_entity_id}/_treeUnmerge", "api", request.tenant_id)
        
        # Add the contributor entity URI as a query parameter
        params = {
            "contributorURI": f"entities/{request.contributor_entity_id}"
        }
        
        try:
            headers = get_reltio_headers()
            headers["Content-Type"] = "application/json"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
        
        # Make the POST request with URL parameters
        try:
            unmerge_result = http_request(
                url, 
                method='POST',
                params=params,
                headers=headers
            )
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"One or more entities not found"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid tree unmerge request: {str(e)}"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to tree unmerge entity"
            )
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"unmerge_entity_tree_by_contributor_tool : Successfully unmerged origin entity {request.origin_entity_id} by contributor entity {request.contributor_entity_id} and all profiles merged beneath it from a merged entity"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for unmerge_entity_tree_by_contributor: {str(log_error)}")
        
        return unmerge_result
    except Exception as e:
        # Log the error
        logger.error(f"Unexpected error in unmerge_entity_tree_by_contributor: {str(e)}")
        
        # Return a sanitized error response
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while tree unmerging entity"
        )
