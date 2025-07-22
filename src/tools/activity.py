"""
Reltio MCP Server - Activity Tools

This module contains functions for retrieving activity events from Reltio.
"""
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote
import yaml
from src.constants import MAX_RESULTS_LIMIT
from src.env import RELTIO_TENANT
from src.util.api import get_reltio_url, http_request, create_error_response, validate_connection_security
from src.util.auth import get_reltio_headers
from src.util.exceptions import SecurityError
from src.util.models import MergeActivitiesRequest
from src.util.activity_log import ActivityLog

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

async def get_merge_activities(
    timestamp_gt: int, 
    event_types: Optional[List[str]] = None, 
    timestamp_lt: Optional[int] = None, 
    entity_type: Optional[str] = None, 
    user: Optional[str] = None, 
    tenant_id: str = RELTIO_TENANT, 
    offset: int = 0, 
    max_results: int = 100
) -> dict:
    """Retrieve activity events related to entity merges with flexible filtering options.
    
    Args:
        timestamp_gt (int): Filter events with timestamp greater than this value (in milliseconds since epoch)
        event_types (Optional[List[str]]): List of merge event types to filter by. Defaults to 
                                         ['ENTITIES_MERGED_MANUALLY', 'ENTITIES_MERGED', 'ENTITIES_MERGED_ON_THE_FLY']
        timestamp_lt (Optional[int]): Optional filter for events with timestamp less than this value (in milliseconds since epoch)
        entity_type (Optional[str]): Optional filter for specific entity type (e.g., 'Individual', 'Organization')
        user (Optional[str]): Optional filter for merges performed by a specific user
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        offset (int): Pagination offset. Defaults to 0.
        max_results (int): Maximum number of results to return. Defaults to 100.
    
    Returns:
        A dictionary containing the activity events matching the specified filters
    
    Raises:
        Exception: If there's an error retrieving the activity events
    
    Examples:
        # Get all merge activities since timestamp 1744191663000
        get_merge_activities(1744191663000)
        
        # Get merge activities within a specific time range
        get_merge_activities(1744191663000, timestamp_lt=1744291663000)
        
        # Get only manual merge activities for a specific entity type
        get_merge_activities(1744191663000, event_types=['ENTITIES_MERGED_MANUALLY'], entity_type='Individual')
    """
    try:
        logger.info(f"Getting merge activities for tenant {tenant_id}")
        
        # Validate parameters using Pydantic model
        try:
            request = MergeActivitiesRequest(
                timestamp_gt=timestamp_gt,
                event_types=event_types,
                timestamp_lt=timestamp_lt,
                entity_type=entity_type,
                user=user,
                tenant_id=tenant_id,
                offset=offset,
                max_results=max_results
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_merge_activities: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Validate max_results
        if max_results < 1:
            max_results = 1
        elif max_results > MAX_RESULTS_LIMIT:
            max_results = MAX_RESULTS_LIMIT
            logger.info(f"Max results limited to {MAX_RESULTS_LIMIT} for merge activities")
        
        try:
            headers = get_reltio_headers()
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio API"
            )
            
        # Default event types if not provided
        if request.event_types is None:
            request.event_types = ['ENTITIES_MERGED_MANUALLY', 'ENTITIES_MERGED', 'ENTITIES_MERGED_ON_THE_FLY']
        
        # Build filter string
        filter_parts = [f"gt(timestamp,{request.timestamp_gt})"]
        
        # Add timestamp_lt condition if provided
        if request.timestamp_lt is not None:
            filter_parts.append(f"lt(timestamp,{request.timestamp_lt})")
        
        # Add event types filter
        event_type_filters = []
        for event_type in request.event_types:
            event_type_filters.append(f"equals(items.data.type,'{event_type}')")
        
        # Combine event type filters with OR
        if event_type_filters:
            if len(event_type_filters) == 1:
                filter_parts.append(event_type_filters[0])
            else:
                filter_parts.append(f"({' OR '.join(event_type_filters)})")
        
        # Add entity type filter if provided
        if request.entity_type is not None:
            filter_parts.append(f"equals(items.objectType,'configuration/entityTypes/{request.entity_type}')")
        
        # Add user filter if provided
        if request.user is not None:
            filter_parts.append(f"equals(user,'{request.user}')")
        
        # Combine all filter parts with AND
        filter_str = " AND ".join(filter_parts)
        
        # URL encode the filter string
        encoded_filter = quote(filter_str)
        
        # Build the URL
        url = get_reltio_url(f"activities?filter={encoded_filter}&offset={request.offset}&max={request.max_results}", "api", request.tenant_id)
        
        # Validate connection security
        try:
            validate_connection_security(url, headers)
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}")
            return create_error_response(
                "AUTHORIZATION_ERROR",
                "Security requirements not met"
            )
        
        # Make the API request
        try:
            response = http_request(url, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check if it's a 404 error (not found)
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    "Activities resource not found"
                )
            
            return create_error_response(
                "SERVER_ERROR",
                "Failed to retrieve activity events from Reltio API"
            )
            
        try:
            merge_activities_ids = [activity.get("uri", "") for activity in response]
            merge_activities_ids_str = ", ".join(merge_activities_ids)
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                description=f"get_merge_activities_tool : MCP server successfully fetched merge activities, merge activities IDs: {merge_activities_ids_str}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_merge_activities: {str(log_error)}")

        return yaml.dump(response,sort_keys=False)
    
    
    except Exception as e:
        error_msg = f"Unexpected error in get_merge_activities: {str(e)}"
        logger.error(error_msg)
        return create_error_response(
            "SERVER_ERROR",
            "An unexpected error occurred while retrieving merge activities"
        ) 