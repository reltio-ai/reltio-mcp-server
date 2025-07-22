import uuid
from typing import Dict, Any
import logging
from src.constants import ACTIVITY_LOG_LABEL
from src.util.api import get_reltio_url, get_reltio_headers, http_request, validate_connection_security, create_error_response

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

class ActivityLog:
    @staticmethod
    def generate_activity_id() -> str:
        """Generate a unique activity ID in the format d7f7-22cd-a022424f"""
        uuid_hex = uuid.uuid4().hex
        return f"{uuid_hex[:4]}-{uuid_hex[4:8]}-{uuid_hex[8:16]}"

    @staticmethod
    def create_request_body(
        description: str
    ) -> Dict[str, Any]:
        """
        Create the request body for activity logging
        
        Args:
            description (str): Description for the activity
            
        Returns:
            Dict[str, Any]: The formatted request body
        """
        return {
            "label": ACTIVITY_LOG_LABEL,
            "description": description
        }

    @staticmethod
    async def log_activity(tenant_id: str, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log an activity by making a POST request to the Reltio activities API
        
        Args:
            tenant_id (str): The tenant ID for the Reltio environment
            request_body (Dict[str, Any]): The request body containing activity details
            
        Returns:
            Dict[str, Any]: The API response
            
        Raises:
            Exception: If there's an error during the API call
        """
        try:
            # Generate unique activity ID
            activity_id = ActivityLog.generate_activity_id()
            
            # Get API URL and headers
            url = get_reltio_url("activities", "api", tenant_id)
            try:
                headers = get_reltio_headers() 
                headers["ActivityID"] = activity_id
                # Validate connection security
                validate_connection_security(url, headers)
            except Exception as e:
                logger.error(f"Authentication or security error: {str(e)}")
                return create_error_response(
                    "AUTHENTICATION_ERROR",
                    "Failed to authenticate with Reltio API"
                )
            
            # Make the API call
            response = http_request(
                method="POST",
                url=url,
                data=request_body,
                headers=headers
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
            raise Exception(f"Failed to log activity: {str(e)}")

    @staticmethod
    async def execute_and_log_activity(
        tenant_id: str,
        description: str
    ) -> Any:
        """
        Log an activity
        
        Args:
            tenant_id (str): The tenant ID for the Reltio environment
            description (str): Description for the activity
            
        Raises:
            Exception: If there's an error during activity logging
        """
        try:
            # Create request body
            request_body = ActivityLog.create_request_body(description)
            
            # Log the activity
            await ActivityLog.log_activity(tenant_id, request_body)
            
        except Exception as e:
            logger.error(f"Error in execute_and_log_activity: {str(e)}")
            raise 