import logging
from typing import List, Dict, Any, Optional
import yaml
import requests
from src.constants import ACTIVITY_CLIENT
from src.env import RELTIO_TENANT, RELTIO_ENVIRONMENT
from src.util.api import (
    create_error_response, 
    validate_connection_security,
    http_request
)
from src.util.auth import get_reltio_headers
from src.util.activity_log import ActivityLog
from src.util.models import GetPossibleAssigneesRequest, RetrieveTasksRequest, GetTaskDetailsRequest, StartProcessInstanceRequest, ExecuteTaskActionRequest
from src.tools.util import ActivityLogLabel

# Configure logging
logger = logging.getLogger("mcp.server.reltio")


def get_workflow_url(endpoint: str, tenant_id: str) -> str:
    """Construct workflow API URL"""
    return f"https://{RELTIO_ENVIRONMENT}-workflowui.reltio.com/services/workflow/{tenant_id}/{endpoint}"


def http_request_workflow(url: str, method: str = 'POST', data=None, headers=None, params=None) -> dict:
    """Make an HTTP request to workflow API and return the JSON response"""
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_message = e.response.text if e.response else str(e)
        raise ValueError(f"Workflow API request failed: {e.response.status_code if e.response else 'Unknown'} - {error_message}")
    except Exception as e:
        raise ValueError(f"Workflow API request failed: {str(e)}")


async def get_user_workflow_tasks(assignee: str, tenant_id: str = RELTIO_TENANT, offset: int = 0, 
                                  max_results: int = 10) -> dict:
    """Get workflow tasks for a specific user with total count and detailed task information
    
    Args:
        assignee (str): Username/assignee to get tasks for
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        offset (int): Starting index for paginated results. Use 0 for the first page. Defaults to 0.
        max_results (int): Maximum number of results to return. Defaults to 10. Set to 1 if you only need the total count.
    
    Returns:
        A dictionary containing the total task count and detailed workflow tasks
    
    Raises:
        Exception: If there's an error getting the workflow tasks
    """
    try:
        # Construct workflow API URL
        url = get_workflow_url("tasks", tenant_id)
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        # Request body with pagination - cap max_results at 100
        request_body = {
            "assignee": assignee,
            "offset": offset,
            "max": min(max_results, 100)
        }
        
        try:
            workflow_response = http_request_workflow(url, method='POST', data=request_body, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve workflow tasks: {str(e)}"
            )
        
        # Extract and filter the required fields from task data
        tasks = []
        if workflow_response.get("data"):
            for task in workflow_response["data"]:
                task_info = {
                    "taskId": task.get("taskId", ""),
                    "processType": task.get("processType", ""),
                    "taskType": task.get("taskType", ""),
                    "createTime": task.get("createTime", None),
                    "dueDate": task.get("dueDate", None),
                    "displayName": task.get("displayName", ""),
                    "priorityClass": task.get("priorityClass", ""),
                    "processDefinitionDisplayName": task.get("processDefinitionDisplayName", ""),
                    "objectURIs": task.get("objectURIs", [])
                }
                tasks.append(task_info)
        
        # Build response with both total count and task details
        result = {
            "assignee": assignee,
            "total_tasks": workflow_response.get("total", 0),
            "returned_count": len(tasks),
            "offset": workflow_response.get("offset", offset),
            "status": workflow_response.get("status", ""),
            "tasks": tasks
        }
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                label=ActivityLogLabel.WORKFLOW_TASKS.value,
                client_type=ACTIVITY_CLIENT,
                description=f"get_user_workflow_tasks_tool : MCP server successfully fetched workflow tasks for user {assignee} (total: {result['total_tasks']}, returned: {len(tasks)})"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_user_workflow_tasks: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Error in get_user_workflow_tasks: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving workflow tasks: {str(e)}"
        )


async def reassign_workflow_task(task_id: str, assignee: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Reassign a workflow task to a different user
    
    Args:
        task_id (str): The ID of the task to reassign
        assignee (str): Username to assign the task to
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the reassignment result
    
    Raises:
        Exception: If there's an error reassigning the workflow task
    """
    try:
        # Construct workflow API URL for specific task
        url = f"https://{RELTIO_ENVIRONMENT}-workflowui.reltio.com/services/workflow/{tenant_id}/tasks"
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        # Request body with new assignee
        request_body = [{
            "taskId": task_id,
            "assignee": assignee
        }]
        
        try:
            reassign_response = http_request_workflow(url, method='PUT', data=request_body, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to reassign workflow task: {str(e)}"
            )
        
        # Build response with reassignment details
        result = {
            "task_id": task_id,
            "new_assignee": assignee,
            "status": reassign_response.get("status", ""),
            "success": reassign_response.get("status", "").upper() == "OK"
        }
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                label=ActivityLogLabel.WORKFLOW_TASKS.value,
                client_type=ACTIVITY_CLIENT,
                description=f"reassign_workflow_task_tool : MCP server successfully reassigned task {task_id} to user {assignee}"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for reassign_workflow_task: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Error in reassign_workflow_task: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while reassigning workflow task: {str(e)}"
        )


async def get_possible_assignees(tenant_id: str = RELTIO_TENANT, tasks: Optional[List[str]] = None, 
                                 task_filter: Optional[Dict[str, Any]] = None, exclude: Optional[List[str]] = None) -> dict:
    """Get possible assignees for specific tasks or based on filter/exclude criteria
    IMPORTANT: Only one parameter approach can be used at a time:
        - Either use 'tasks' parameter alone, OR
        - Use 'task_filter' and/or 'exclude' parameters (but NOT with 'tasks')
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        tasks (Optional[List[str]]): List of task IDs to get possible assignees for.
        task_filter (Optional[Dict[str, Any]]): Filter criteria for tasks, Parameters used as filtering criteria for the resulting tasks list.
        exclude (Optional[List[str]]): List of task IDs to exclude.
    
    Returns:
        A dictionary containing the possible assignees data and total count
    
    Raises:
        Exception: If there's an error getting the possible assignees
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = GetPossibleAssigneesRequest(
                tenant_id=tenant_id,
                tasks=tasks,
                task_filter=task_filter,
                exclude=exclude
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_possible_assignees: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Construct workflow API URL for assignees
        url = f"https://{RELTIO_ENVIRONMENT}-workflowui.reltio.com/services/workflow/{request.tenant_id}/assignee"
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        # Build request body from Pydantic model
        request_body = {}
        
        if request.tasks:
            request_body["tasks"] = request.tasks
        else:
            # For filter/exclude approach, always include filter field (even if empty)
            request_body["filter"] = request.task_filter if request.task_filter else {}
            if request.exclude:
                request_body["exclude"] = request.exclude
        
        try:
            assignees_response = http_request_workflow(url, method='POST', data=request_body, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve possible assignees: {str(e)}"
            )
        
        # Build response with assignees data
        result = {
            "status": assignees_response.get("status", ""),
            "data": assignees_response.get("data", []),
            "total": assignees_response.get("total", 0),
            "request_parameters": {
                "tenant_id": request.tenant_id,
                "tasks": request.tasks if request.tasks else None,
                "filter": request.task_filter if request.task_filter else None,
                "exclude": request.exclude if request.exclude else None
            }
        }
        
        # Add warning if present
        if assignees_response.get("warning"):
            result["warning"] = assignees_response["warning"]
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=request.tenant_id,
                label=ActivityLogLabel.WORKFLOW_TASKS.value,
                client_type=ACTIVITY_CLIENT,
                description=f"get_possible_assignees_tool : MCP server successfully retrieved possible assignees (total: {result['total']})"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for get_possible_assignees: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Error in get_possible_assignees: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving possible assignees: {str(e)}"
        )


async def retrieve_tasks(
    tenant_id: str = RELTIO_TENANT,
    assignee: Optional[str] = None,
    process_instance_id: Optional[str] = None,
    process_type: Optional[str] = None,
    process_types: Optional[List[str]] = None,
    offset: int = 0,
    max_results: int = 10,
    suspended: Optional[bool] = None,
    created_by: Optional[str] = None,
    priority_class: Optional[str] = None,
    order_by: str = "createTime",
    ascending: bool = False,
    task_type: Optional[str] = None,
    created_after: Optional[int] = None,
    created_before: Optional[int] = None,
    state: str = "valid",
    object_uris: Optional[List[str]] = None,
    show_task_variables: bool = False,
    show_task_local_variables: bool = False,
    object_filter: Optional[str] = None
) -> dict:
    """Retrieve tasks by filter
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment
        assignee (str, optional): Task assignee. To retrieve unassigned tasks, use a value of 'none'
        process_instance_id (str, optional): Process instance ID
        process_type (str, optional): Process instance type
        process_types (List[str], optional): Process instance types to filter on
        offset (int): Start position, default 0
        max_results (int): Number of records to be returned, default 10
        suspended (bool, optional): Filter by suspended status
        created_by (str, optional): Task owner
        priority_class (str, optional): Priority class (Urgent, High, Medium, Low)
        order_by (str): Sort criteria (createTime, assignee, dueDate, priority), default createTime
        ascending (bool): Sort order, default False (descending)
        task_type (str, optional): Task type
        created_after (int, optional): Time in milliseconds
        created_before (int, optional): Time in milliseconds
        state (str): Validation state (valid, invalid, all), default valid
        object_uris (List[str], optional): List of Reltio object URIs (entity/relation)
        show_task_variables (bool): Display task variables, default False
        show_task_local_variables (bool): Display task local variables, default False
        object_filter (str, optional): Search filter expression for linked entities
    
    Returns:
        A dictionary containing task results with pagination info
    
    Raises:
        Exception: If there's an error retrieving the tasks
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = RetrieveTasksRequest(
                tenant_id=tenant_id,
                assignee=assignee,
                process_instance_id=process_instance_id,
                process_type=process_type,
                process_types=process_types,
                offset=offset,
                max_results=max_results,
                suspended=suspended,
                created_by=created_by,
                priority_class=priority_class,
                order_by=order_by,
                ascending=ascending,
                task_type=task_type,
                created_after=created_after,
                created_before=created_before,
                state=state,
                object_uris=object_uris,
                show_task_variables=show_task_variables,
                show_task_local_variables=show_task_local_variables,
                object_filter=object_filter
            )
        except ValueError as e:
            logger.warning(f"Validation error in retrieve_tasks: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Construct workflow API URL
        url = f"https://{RELTIO_ENVIRONMENT}-workflowui.reltio.com/services/workflow/{request.tenant_id}/tasks"
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        params = {"checkAccess": True}
        
        # Use Pydantic's model_dump with serialization aliases and exclude None values
        request_body = request.model_dump(
            by_alias=True,  # Use serialization aliases
            exclude_none=True,  # Exclude None values
            exclude_unset=False  # Include fields with default values
        )
        
        # Apply max_results cap of 100 if present
        if "max" in request_body:
            request_body["max"] = min(request_body["max"], 100)
        
        try:
            workflow_response = http_request_workflow(url, method='POST', data=request_body, headers=headers, params=params)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve workflow tasks: {str(e)}"
            )
        
        # Check if the response status indicates failure
        if workflow_response.get("status") == "failed":
            # Handle failed status - return only status and error
            error_info = workflow_response.get("error", {})
            error_code = error_info.get("errorCode", "Unknown")
            error_message = error_info.get("errorMessage", "Unknown error")
            
            logger.error(f"Workflow API returned failed status: {error_code} - {error_message}")
            
            # Return the failed response as-is with only status and error
            return yaml.dump({
                "status": "failed",
                "error": workflow_response.get("error", {
                    "errorCode": error_code,
                    "errorMessage": error_message
                })
            }, sort_keys=False)
        
        # Extract the data from response for successful cases
        tasks = workflow_response.get("data", [])
        
        # Build response with all relevant information
        result = {
            "offset": workflow_response.get("offset", request.offset),
            "size": workflow_response.get("size", len(tasks)),
            "total": workflow_response.get("total", 0),
            "data": tasks,
            "status": workflow_response.get("status")
        }
        
        # Add warning if present (for successful responses that may have warnings)
        if "warning" in workflow_response:
            result["warning"] = workflow_response["warning"]
        
        # Only log activity for successful responses
        if result.get("status") == "OK":
            try:
                # Create description for activity log
                description_parts = ["retrieve_tasks_tool : MCP server successfully retrieved workflow tasks"]
                if request.assignee:
                    description_parts.append(f"for assignee {request.assignee}")
                if request.process_types:
                    description_parts.append(f"of types {', '.join(request.process_types)}")
                if request.task_type:
                    description_parts.append(f"of task type {request.task_type}")
                description_parts.append(f"(total: {result['total']}, returned: {len(tasks)})")
                
                await ActivityLog.execute_and_log_activity(
                    tenant_id=request.tenant_id,
                    label=ActivityLogLabel.WORKFLOW_TASKS.value,
                    client_type=ACTIVITY_CLIENT,
                    description=" ".join(description_parts)
                )
            except Exception as log_error:
                logger.error(f"Activity logging failed for retrieve_tasks: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Error in retrieve_tasks: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving workflow tasks: {str(e)}"
        )


async def get_task_details(
    task_id: str,
    tenant_id: str = RELTIO_TENANT,
    show_task_variables: bool = False,
    show_task_local_variables: bool = False
) -> dict:
    """Get details of a specific workflow task by ID
    
    Args:
        task_id (str): The ID of the task to retrieve details for
        tenant_id (str): Tenant ID for the Reltio environment
        show_task_variables (bool): Display task variables, default False
        show_task_local_variables (bool): Display task local variables, default False
    
    Returns:
        A dictionary containing complete task details
    
    Raises:
        Exception: If there's an error retrieving the task details
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = GetTaskDetailsRequest(
                task_id=task_id,
                tenant_id=tenant_id,
                show_task_variables=show_task_variables,
                show_task_local_variables=show_task_local_variables
            )
        except ValueError as e:
            logger.warning(f"Validation error in get_task_details: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Construct workflow API URL
        url = f"https://{RELTIO_ENVIRONMENT}-workflowui.reltio.com/services/workflow/{request.tenant_id}/tasks/{request.task_id}"
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        # Build query parameters
        params = {}
        if request.show_task_variables:
            params["showTaskVariables"] = "true"
        if request.show_task_local_variables:
            params["showTaskLocalVariables"] = "true"
        
        try:
            workflow_response = http_request_workflow(url, method='GET', headers=headers, params=params)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to retrieve task details: {str(e)}"
            )
        
        # Check if the response status indicates failure
        if workflow_response.get("status") == "failed":
            # Handle failed status - return only status and error
            error_info = workflow_response.get("error", {})
            error_code = error_info.get("errorCode", "Unknown")
            error_message = error_info.get("errorMessage", "Unknown error")
            
            logger.error(f"Workflow API returned failed status: {error_code} - {error_message}")
            
            # Return the failed response as-is with only status and error
            return yaml.dump({
                "status": "failed",
                "error": workflow_response.get("error", {
                    "errorCode": error_code,
                    "errorMessage": error_message
                })
            }, sort_keys=False)
        
        # For successful responses, add warning if present
        result = workflow_response.copy()
        
        # Only log activity for successful responses
        if result.get("status") == "OK":
            try:
                # Create description for activity log
                task_display_name = result.get("displayName", "Unknown Task")
                assignee = result.get("assignee", "Unassigned")
                process_type = result.get("processType", "Unknown Process")
                
                description = f"get_task_details_tool : MCP server successfully retrieved details for task {request.task_id} ({task_display_name}) assigned to {assignee} of type {process_type}"
                
                await ActivityLog.execute_and_log_activity(
                    tenant_id=request.tenant_id,
                    label=ActivityLogLabel.WORKFLOW_TASKS.value,
                    client_type=ACTIVITY_CLIENT,
                    description=description
                )
            except Exception as log_error:
                logger.error(f"Activity logging failed for get_task_details: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Error in get_task_details: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An error occurred while retrieving task details: {str(e)}"
        )


async def start_process_instance(
    process_type: str, 
    object_uris: List[str], 
    tenant_id: str = RELTIO_TENANT,
    comment: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None
) -> dict:
    """Start a process instance in Reltio workflow
    
    Args:
        process_type (str): The type of process to start (e.g., 'DataChangeRequest', 'MergeRequest')
        object_uris (List[str]): List of object URIs to associate with the process instance
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        comment (Optional[str]): Optional comment for the process instance
        variables (Optional[Dict[str, Any]]): Optional variables to pass to the process instance
    
    Returns:
        A dictionary containing the process instance details including processInstanceId, processType, and status
    
    Raises:
        Exception: If there's an error starting the process instance
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = StartProcessInstanceRequest(
                tenant_id=tenant_id,
                process_type=process_type,
                object_uris=object_uris,
                comment=comment,
                variables=variables
            )
        except ValueError as e:
            logger.warning(f"Validation error in start_process_instance: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Construct workflow API URL for starting process instances
        url = f"https://{RELTIO_ENVIRONMENT}.reltio.com/nui/workflow/workflow/{request.tenant_id}/processInstances"
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            headers["Globalid"] = ACTIVITY_CLIENT
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                "Failed to authenticate with Reltio Workflow API"
            )
        
        # Prepare request body
        request_body = {
            "processType": request.process_type,
            "objectURIs": request.object_uris
        }
        
        # Add optional fields if provided
        if request.comment:
            request_body["comment"] = request.comment
        if request.variables:
            request_body["variables"] = request.variables
        
        try:
            process_response = http_request(url, method='POST', data=request_body, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Process type '{process_type}' not found or invalid"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid process instance request: {str(e)}"
                )
            elif "403" in str(e):
                return create_error_response(
                    "PERMISSION_DENIED",
                    f"Insufficient permissions to start process instance: {str(e)}"
                )
            
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to start process instance: {str(e)}"
            )
        
        # Build response with process instance details
        result = {
            "processInstanceId": process_response.get("processInstanceId", ""),
            "processType": request.process_type,
            "objectURIs": request.object_uris,
            "status": process_response.get("status", "STARTED"),
        }
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                label=ActivityLogLabel.WORKFLOW_TASKS.value,
                client_type=ACTIVITY_CLIENT,
                description=f"start_process_instance_tool : Successfully started process instance {result['processInstanceId']} of type {process_type} for {len(object_uris)} objects"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for start_process_instance: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Unexpected error in start_process_instance: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An unexpected error occurred while starting process instance: {str(e)}"
        )


async def execute_task_action(
    task_id: str,
    action: str,
    tenant_id: str = RELTIO_TENANT,
    process_instance_comment: Optional[str] = None
) -> dict:
    """Execute an action on a workflow task
    
    Args:
        task_id (str): The ID of the task to execute action on
        action (str): The action to execute (e.g., 'Approve', 'Reject')
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        process_instance_comment (Optional[str]): Optional comment for the process instance
    
    Returns:
        A dictionary containing the action execution result including taskId, action, and status
    
    Raises:
        Exception: If there's an error executing the task action
    """
    try:
        # Validate inputs using Pydantic model
        try:
            request = ExecuteTaskActionRequest(
                tenant_id=tenant_id,
                task_id=task_id,
                action=action,
                process_instance_comment=process_instance_comment
            )
        except ValueError as e:
            logger.warning(f"Validation error in execute_task_action: {str(e)}")
            return create_error_response(
                "VALIDATION_ERROR",
                f"Invalid request parameters: {str(e)}"
            )
        
        # Construct workflow API URL for executing task action
        url = get_workflow_url(f"tasks/{request.task_id}/_action", request.tenant_id)
        
        try:
            headers = get_reltio_headers()
            headers['Content-Type'] = 'application/json'
            headers['EnvironmentURL'] = f"https://{RELTIO_ENVIRONMENT}.reltio.com"
            headers["Globalid"] = ACTIVITY_CLIENT
            
            # Validate connection security
            validate_connection_security(url, headers)
        except Exception as e:
            logger.error(f"Authentication or security error: {str(e)}")
            return create_error_response(
                "AUTHENTICATION_ERROR",
                f"Failed to authenticate with Reltio Workflow API-{str(e)}"
            )
        
        # Prepare request body
        request_body = {
            "action": request.action
        }
        
        # Add optional comment if provided
        if request.process_instance_comment:
            request_body["processInstanceComment"] = request.process_instance_comment
        
        try:
            action_response = http_request(url, method='POST', data=request_body, headers=headers)
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            
            # Check for common errors
            if "404" in str(e):
                return create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Task '{task_id}' not found or invalid"
                )
            elif "400" in str(e):
                return create_error_response(
                    "INVALID_REQUEST",
                    f"Invalid action request: {str(e)}"
                )
            elif "403" in str(e):
                return create_error_response(
                    "PERMISSION_DENIED",
                    f"Insufficient permissions to execute action on task: {str(e)}"
                )
            elif "409" in str(e):
                return create_error_response(
                    "CONFLICT",
                    f"Task action cannot be executed due to current task state: {str(e)}"
                )
            
            return create_error_response(
                "API_REQUEST_ERROR",
                f"Failed to execute task action: {str(e)}"
            )
        
        # Build response with action execution details
        result = {
            "taskId": request.task_id,
            "action": request.action,
            "status": action_response.get("status", "UNKNOWN"),
            "success": action_response.get("status", "").upper() == "OK"
        }
        
        # Add comment if provided
        if request.process_instance_comment:
            result["comment"] = request.process_instance_comment
        
        try:
            await ActivityLog.execute_and_log_activity(
                tenant_id=tenant_id,
                label=ActivityLogLabel.WORKFLOW_TASKS.value,
                client_type=ACTIVITY_CLIENT,
                description=f"execute_task_action_tool : Successfully executed action '{action}' on task {task_id} with status '{result['status']}'"
            )
        except Exception as log_error:
            logger.error(f"Activity logging failed for execute_task_action: {str(log_error)}")
        
        return yaml.dump(result, sort_keys=False)
        
    except Exception as e:
        logger.error(f"Unexpected error in execute_task_action: {str(e)}")
        return create_error_response(
            "INTERNAL_SERVER_ERROR",
            f"An unexpected error occurred while executing task action: {str(e)}"
        )
