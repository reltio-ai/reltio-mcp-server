import pytest
import yaml
from unittest.mock import patch, MagicMock, AsyncMock
from src.tools.workflow import (
    get_user_workflow_tasks,
    reassign_workflow_task,
    http_request_workflow,
    get_possible_assignees,
    retrieve_tasks,
    get_task_details,
    start_process_instance,
    execute_task_action
)

TENANT_ID = "test-tenant"
ASSIGNEE = "testuser"
TASK_ID = "task-123"
NEW_ASSIGNEE = "newuser"
OFFSET = 0
MAX_RESULTS = 10
PROCESS_TYPE = "DataChangeRequest"
OBJECT_URIS = ["entities/123", "entities/456"]
ACTION = "Approve"
COMMENT = "Task approved for processing"

# Mock workflow data for testing
MOCK_WORKFLOW_RESPONSE = {
    "data": [
        {
            "taskId": "task-123",
            "processType": "review",
            "taskType": "approval",
            "createTime": "2024-01-01T10:00:00Z",
            "dueDate": "2024-01-15T10:00:00Z",
            "displayName": "Review Task 1",
            "priorityClass": "high",
            "processDefinitionDisplayName": "Entity Review Process",
            "objectURIs": ["entities/123", "entities/456"]
        },
        {
            "taskId": "task-456",
            "processType": "merge",
            "taskType": "decision",
            "createTime": "2024-01-02T15:30:00Z",
            "dueDate": "2024-01-16T15:30:00Z",
            "displayName": "Merge Decision Task",
            "priorityClass": "medium",
            "processDefinitionDisplayName": "Entity Merge Process",
            "objectURIs": ["entities/789"]
        }
    ],
    "total": 2,
    "offset": 0,
    "status": "success"
}

MOCK_REASSIGN_RESPONSE = {
    "success": True,
    "message": "Task reassigned successfully",
    "taskId": TASK_ID,
    "newAssignee": NEW_ASSIGNEE,
    "status": "OK"
}

MOCK_REASSIGN_FAILURE_RESPONSE = {
    "success": False,
    "message": "Task not found",
    "error": "TASK_NOT_FOUND",
    "status": "ERROR"
}

MOCK_WORKFLOW_RESPONSE_WITH_MISSING_FIELDS = {
    "data": [
        {
            "taskId": "task-123",
            "processType": "review",
            # Missing other fields
        }
    ],
    "total": 1
}

MOCK_WORKFLOW_RESPONSE_WITH_NULL_FIELDS = {
    "data": [
        {
            "taskId": "task-123",
            "processType": "review",
            "taskType": "approval",
            "createTime": None,
            "dueDate": None,
            "displayName": None,
            "priorityClass": None,
            "processDefinitionDisplayName": None,
            "objectURIs": None
        }
    ],
    "total": 1
}

# Mock assignees data for testing
MOCK_ASSIGNEES_RESPONSE = {
    "status": "OK",
    "data": [
        "wf_user1",
        "wf_user2", 
        "wf_user5",
        "wf_user7"
    ],
    "total": 4
}

MOCK_ASSIGNEES_EMPTY_RESPONSE = {
    "status": "OK",
    "data": [],
    "total": 0
}

# Mock data for retrieve_tasks tests
MOCK_RETRIEVE_TASKS_SUCCESS_RESPONSE = {
    "data": [
        {
            "taskId": "task-001",
            "assignee": "john.doe@company.com",
            "createTime": 1640995200000,
            "createdBy": "system.admin",
            "dueDate": 1641081600000,
            "displayName": "Data Change Request Review",
            "processInstanceId": "23164186",
            "processTypes": ["dataChangeRequestReview"],
            "processDefinitionDisplayName": "DCR Review Process",
            "taskType": "dcrReview",
            "suspended": False,
            "objectURIs": ["changeRequests/AeFAoBPn", "entities/16lJbKKs"],
            "possibleActions": ["approve", "reject", "requestMoreInfo"],
            "preferredAction": "approve",
            "priority": 50,
            "priorityClass": "Medium",
            "repeatingTask": False,
            "validationMessage": "Task is valid",
            "variableMap": {"entityId": "16lJbKKs"}
        }
    ],
    "offset": 0,
    "status": "OK",
    "total": 1
}

# Mock data for start_process_instance tests
MOCK_START_PROCESS_SUCCESS_RESPONSE = {
    "processInstanceId": "12345678",
    "status": "started",
    "message": "Process instance started successfully"
}

# Mock data for execute_task_action tests
MOCK_EXECUTE_ACTION_SUCCESS_RESPONSE = {
    "taskId": TASK_ID,
    "action": ACTION,
    "status": "completed",
    "message": "Action executed successfully"
}

# Mock data for get_task_details tests
MOCK_TASK_DETAILS_RESPONSE = {
    "taskId": TASK_ID,
    "assignee": ASSIGNEE,
    "createTime": 1640995200000,
    "dueDate": 1641081600000,
    "displayName": "Task Details",
    "processTypes": ["review"],
    "taskType": "approval",
    "objectURIs": OBJECT_URIS,
    "possibleActions": ["approve", "reject"],
    "status": "OK"
}


@pytest.mark.asyncio
class TestGetUserWorkflowTasks:
    """Test suite for get_user_workflow_tasks function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_get_user_workflow_tasks_success(self, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful workflow tasks retrieval"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_WORKFLOW_RESPONSE
        mock_log.return_value = None
        
        result = await get_user_workflow_tasks(ASSIGNEE, TENANT_ID, OFFSET, MAX_RESULTS)
        
        # Parse YAML result
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["assignee"] == ASSIGNEE
        assert parsed_result["total_tasks"] == 2
        assert "tasks" in parsed_result
        assert len(parsed_result["tasks"]) == 2
        
        # Check first task details
        first_task = parsed_result["tasks"][0]
        assert first_task["taskId"] == "task-123"
        assert first_task["processType"] == "review"
        assert first_task["taskType"] == "approval"
        assert first_task["priorityClass"] == "high"
        
        mock_request.assert_called_once()
        mock_log.assert_called_once()

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_get_user_workflow_tasks_auth_error(self, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await get_user_workflow_tasks(ASSIGNEE, TENANT_ID, OFFSET, MAX_RESULTS)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_get_user_workflow_tasks_api_error(self, mock_validate, mock_headers, mock_request):
        """Test API request error handling"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.side_effect = Exception("API failed")
        
        result = await get_user_workflow_tasks(ASSIGNEE, TENANT_ID, OFFSET, MAX_RESULTS)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "API_REQUEST_ERROR"

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_get_user_workflow_tasks_empty_response(self, mock_validate, mock_headers, mock_request, mock_log):
        """Test workflow tasks with empty response"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = {"data": [], "total": 0}
        mock_log.return_value = None
        
        result = await get_user_workflow_tasks(ASSIGNEE, TENANT_ID, OFFSET, MAX_RESULTS)
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["total_tasks"] == 0
        assert len(parsed_result["tasks"]) == 0

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_get_user_workflow_tasks_max_results_capped(self, mock_validate, mock_headers, mock_request, mock_log):
        """Test that max_results is capped at 100"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_WORKFLOW_RESPONSE
        mock_log.return_value = None
        
        # Test with max_results > 100
        await get_user_workflow_tasks(ASSIGNEE, TENANT_ID, OFFSET, 150)
        
        # Verify that the request was made with max_results capped at 100
        call_args = mock_request.call_args
        # http_request_workflow is called with data parameter
        request_data = call_args.kwargs['data']
        assert request_data['max'] == 100


@pytest.mark.asyncio
class TestReassignWorkflowTask:
    """Test suite for reassign_workflow_task function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_reassign_workflow_task_success(self, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful workflow task reassignment"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_REASSIGN_RESPONSE
        mock_log.return_value = None
        
        result = await reassign_workflow_task(TASK_ID, NEW_ASSIGNEE, TENANT_ID)
        
        # Parse YAML result
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["task_id"] == TASK_ID
        assert parsed_result["new_assignee"] == NEW_ASSIGNEE
        assert parsed_result["success"] == True
        assert parsed_result["status"] == "OK"
        
        mock_request.assert_called_once()
        mock_log.assert_called_once()

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_reassign_workflow_task_auth_error(self, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await reassign_workflow_task(TASK_ID, NEW_ASSIGNEE, TENANT_ID)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_reassign_workflow_task_api_error(self, mock_validate, mock_headers, mock_request):
        """Test API request error handling"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.side_effect = Exception("API failed")
        
        result = await reassign_workflow_task(TASK_ID, NEW_ASSIGNEE, TENANT_ID)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "API_REQUEST_ERROR"

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    async def test_reassign_workflow_task_failure_response(self, mock_validate, mock_headers, mock_request, mock_log):
        """Test workflow task reassignment with failure response"""
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_REASSIGN_FAILURE_RESPONSE
        mock_log.return_value = None
        
        result = await reassign_workflow_task(TASK_ID, NEW_ASSIGNEE, TENANT_ID)
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["success"] == False
        assert parsed_result["status"] == "ERROR"


@pytest.mark.asyncio
class TestGetPossibleAssignees:
    """Test suite for get_possible_assignees function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.GetPossibleAssigneesRequest")
    async def test_get_possible_assignees_success(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful retrieval of possible assignees"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.tasks = [TASK_ID]
        mock_request_obj.task_filter = None
        mock_request_obj.exclude = None
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_ASSIGNEES_RESPONSE
        mock_log.return_value = None
        
        result = await get_possible_assignees(TENANT_ID, tasks=[TASK_ID])
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["total"] == 4
        assert len(parsed_result["data"]) == 4
        assert "wf_user1" in parsed_result["data"]

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.GetPossibleAssigneesRequest")
    async def test_get_possible_assignees_auth_error(self, mock_request_model, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.tasks = [TASK_ID]
        mock_request_obj.task_filter = None
        mock_request_obj.exclude = None
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await get_possible_assignees(TENANT_ID, tasks=[TASK_ID])
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.GetPossibleAssigneesRequest")
    async def test_get_possible_assignees_empty_response(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test empty assignees list"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.tasks = [TASK_ID]
        mock_request_obj.task_filter = None
        mock_request_obj.exclude = None
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_ASSIGNEES_EMPTY_RESPONSE
        mock_log.return_value = None
        
        result = await get_possible_assignees(TENANT_ID, tasks=[TASK_ID])
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["total"] == 0
        assert len(parsed_result["data"]) == 0


@pytest.mark.asyncio
class TestRetrieveTasks:
    """Test suite for retrieve_tasks function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.RetrieveTasksRequest")
    async def test_retrieve_tasks_success(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful tasks retrieval"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.offset = OFFSET
        mock_request_obj.max_results = MAX_RESULTS
        # Add model_dump method to return proper dict
        mock_request_obj.model_dump.return_value = {
            "offset": OFFSET,
            "max": MAX_RESULTS
        }
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_RETRIEVE_TASKS_SUCCESS_RESPONSE
        mock_log.return_value = None
        
        result = await retrieve_tasks(TENANT_ID, offset=OFFSET, max_results=MAX_RESULTS)
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["total"] == 1
        assert len(parsed_result["data"]) == 1
        
        first_task = parsed_result["data"][0]
        assert first_task["taskId"] == "task-001"
        assert first_task["assignee"] == "john.doe@company.com"
        assert first_task["taskType"] == "dcrReview"

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.RetrieveTasksRequest")
    async def test_retrieve_tasks_auth_error(self, mock_request_model, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.offset = OFFSET
        mock_request_obj.max_results = MAX_RESULTS
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await retrieve_tasks(TENANT_ID, offset=OFFSET, max_results=MAX_RESULTS)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.RetrieveTasksRequest")
    async def test_retrieve_tasks_api_error(self, mock_request_model, mock_validate, mock_headers, mock_request):
        """Test API request error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.offset = OFFSET
        mock_request_obj.max_results = MAX_RESULTS
        mock_request_obj.model_dump.return_value = {
            "offset": OFFSET,
            "max": MAX_RESULTS
        }
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.side_effect = Exception("API failed")
        
        result = await retrieve_tasks(TENANT_ID, offset=OFFSET, max_results=MAX_RESULTS)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "API_REQUEST_ERROR"


@pytest.mark.asyncio
class TestGetTaskDetails:
    """Test suite for get_task_details function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request_workflow")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.GetTaskDetailsRequest")
    async def test_get_task_details_success(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful task details retrieval"""
        mock_request_model.return_value.task_id = TASK_ID
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_request_model.return_value.show_task_variables = False
        mock_request_model.return_value.show_task_local_variables = False
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_TASK_DETAILS_RESPONSE
        mock_log.return_value = None
        
        result = await get_task_details(TASK_ID, TENANT_ID)
        
        parsed_result = yaml.safe_load(result)
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["taskId"] == TASK_ID
        assert parsed_result["assignee"] == ASSIGNEE
        assert parsed_result["taskType"] == "approval"
        assert "possibleActions" in parsed_result

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.GetTaskDetailsRequest")
    async def test_get_task_details_auth_error(self, mock_request_model, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_request_model.return_value.task_id = TASK_ID
        mock_request_model.return_value.tenant_id = TENANT_ID
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await get_task_details(TASK_ID, TENANT_ID)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"


@pytest.mark.asyncio
class TestStartProcessInstance:
    """Test suite for start_process_instance function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.StartProcessInstanceRequest")
    async def test_start_process_instance_success(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful process instance start"""
        mock_request_obj = MagicMock()
        mock_request_obj.process_type = PROCESS_TYPE
        mock_request_obj.object_uris = OBJECT_URIS
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.comment = None
        mock_request_obj.variables = None
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_START_PROCESS_SUCCESS_RESPONSE
        mock_log.return_value = None
        
        result = await start_process_instance(PROCESS_TYPE, OBJECT_URIS, TENANT_ID)
        
        # Result can be YAML string (success) or dict (error)
        if isinstance(result, str):
            parsed_result = yaml.safe_load(result)
        else:
            parsed_result = result
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["processInstanceId"] == "12345678"
        assert parsed_result["status"] == "started"
        assert parsed_result["processType"] == PROCESS_TYPE
        assert parsed_result["objectURIs"] == OBJECT_URIS

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.StartProcessInstanceRequest")
    async def test_start_process_instance_auth_error(self, mock_request_model, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.processType = PROCESS_TYPE
        mock_request_obj.objectURIs = OBJECT_URIS
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.comment = None
        mock_request_obj.variables = None
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await start_process_instance(PROCESS_TYPE, OBJECT_URIS, TENANT_ID)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.http_request")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.StartProcessInstanceRequest")
    async def test_start_process_instance_validation_error(self, mock_request_model, mock_validate, mock_headers, mock_request):
        """Test validation error for invalid process type"""
        mock_request_model.side_effect = ValueError("Invalid process type")
        
        result = await start_process_instance("InvalidType", OBJECT_URIS, TENANT_ID)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
class TestExecuteTaskAction:
    """Test suite for execute_task_action function"""

    @patch("src.tools.workflow.ActivityLog.execute_and_log_activity", new_callable=AsyncMock)
    @patch("src.tools.workflow.http_request")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.ExecuteTaskActionRequest")
    async def test_execute_task_action_success(self, mock_request_model, mock_validate, mock_headers, mock_request, mock_log):
        """Test successful task action execution"""
        mock_request_obj = MagicMock()
        mock_request_obj.task_id = TASK_ID
        mock_request_obj.action = ACTION
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.process_instance_comment = COMMENT
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.return_value = MOCK_EXECUTE_ACTION_SUCCESS_RESPONSE
        mock_log.return_value = None
        
        result = await execute_task_action(TASK_ID, ACTION, TENANT_ID, COMMENT)
        
        # Result can be YAML string (success) or dict (error)
        if isinstance(result, str):
            parsed_result = yaml.safe_load(result)
        else:
            parsed_result = result
        
        assert isinstance(parsed_result, dict)
        assert parsed_result["taskId"] == TASK_ID
        assert parsed_result["action"] == ACTION
        assert parsed_result["status"] == "completed"

    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.ExecuteTaskActionRequest")
    async def test_execute_task_action_auth_error(self, mock_request_model, mock_validate, mock_headers):
        """Test authentication error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.task_id = TASK_ID
        mock_request_obj.action = ACTION
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.process_instance_comment = COMMENT
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_validate.side_effect = Exception("Auth failed")
        
        result = await execute_task_action(TASK_ID, ACTION, TENANT_ID, COMMENT)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "AUTHENTICATION_ERROR"

    @patch("src.tools.workflow.http_request")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.ExecuteTaskActionRequest")
    async def test_execute_task_action_api_error(self, mock_request_model, mock_validate, mock_headers, mock_request):
        """Test API request error handling"""
        mock_request_obj = MagicMock()
        mock_request_obj.task_id = TASK_ID
        mock_request_obj.action = ACTION
        mock_request_obj.tenant_id = TENANT_ID
        mock_request_obj.process_instance_comment = COMMENT
        mock_request_model.return_value = mock_request_obj
        
        mock_headers.return_value = {"Authorization": "Bearer token"}
        mock_request.side_effect = ValueError("Workflow API request failed: 400 - {\"status\":\"failed\",\"error\":{\"errorCode\":10061,\"errorMessage\":\"Tenant [test-tenant] is not registered.\",\"errorData\":{\"exception\":\"com.reltio.workflow.core.KeyedException: Tenant [test-tenant] is not registered.\"}}}")
        
        result = await execute_task_action(TASK_ID, ACTION, TENANT_ID, COMMENT)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "INVALID_REQUEST"

    @patch("src.tools.workflow.http_request")
    @patch("src.tools.workflow.get_reltio_headers")
    @patch("src.tools.workflow.validate_connection_security")
    @patch("src.tools.workflow.ExecuteTaskActionRequest")
    async def test_execute_task_action_validation_error(self, mock_request_model, mock_validate, mock_headers, mock_request):
        """Test validation error for invalid action"""
        mock_request_model.side_effect = ValueError("Invalid action")
        
        result = await execute_task_action(TASK_ID, "InvalidAction", TENANT_ID, COMMENT)
        
        assert isinstance(result, dict)
        assert result["error"]["code_key"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
class TestHttpRequestWorkflow:
    """Test suite for http_request_workflow function"""

    @patch("src.tools.workflow.requests.request")
    def test_http_request_workflow_success(self, mock_request):
        """Test successful HTTP request to workflow API"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response
        
        result = http_request_workflow(
            "https://workflow.reltio.com/api/test",
            method="POST",
            data={"key": "value"},
            headers={"Authorization": "Bearer token"}
        )
        
        assert result == {"status": "success"}
        mock_request.assert_called_once()

    @patch("src.tools.workflow.requests.request")
    def test_http_request_workflow_http_error(self, mock_request):
        """Test HTTP error handling"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_request.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            http_request_workflow(
                "https://workflow.reltio.com/api/test",
                method="POST"
            )
        
        assert "Workflow API request failed" in str(exc_info.value)

    @patch("src.tools.workflow.requests.request")
    def test_http_request_workflow_timeout(self, mock_request):
        """Test timeout error handling"""
        mock_request.side_effect = Exception("Connection timeout")
        
        with pytest.raises(ValueError) as exc_info:
            http_request_workflow(
                "https://workflow.reltio.com/api/test",
                method="GET"
            )
        
        assert "Workflow API request failed" in str(exc_info.value)

