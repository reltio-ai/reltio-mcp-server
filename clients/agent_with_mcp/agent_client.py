#!/usr/bin/env python3
"""
Reltio MCP Client Chat Bot

A CLI chat bot that connects to Reltio MCP server using OAuth 2.0 authentication
and provides an interactive interface for querying Reltio data.
"""

import asyncio
import base64
import http.server
import os
import signal
import sys
import threading
import time
import urllib.parse
import webbrowser
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# ─────────── Configuration Constants ───────────

NAMESPACE="reltio_namespace" #namespace of the reltio instance
RELTIO_CLIENT_ID = "client_id"#client id of the reltio instance you can use reltio_ui
RELTIO_CLIENT_SECRET = "client_secret"#client secret of the reltio instance you can use makita

# User Configuration - Only these need to be set by user
MODEL_ID = "anthropic:claude-3-5-sonnet-20241022"  # model id should be in the format of provider:model_id example: anthropic:claude-3-5-sonnet-20241022,google_genai:gemini-2.0-flash-001,openai:gpt-4o-mini
API_KEY = "API_KEY"  # User provides api key for the model provider

# Environment variable names for different providers
ENV_VAR_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "google_genai": "GOOGLE_API_KEY"
}

##use this to configure model settings based on your needs
model_configs={
    "temperature":0.1,
    # "max_tokens":300,
    # "top_p":1,
}

##system prompt for the agent
SYSTEM_PROMPT = """You are a helpful AI assistant that works with Reltio data. 
Provide detailed and comprehensive answers, don't skip important details.
Be helpful, accurate, and thorough in your responses."""


# Global flag for graceful shutdown
shutdown_flag = False
DEBUG_MODE=False ##if you want to see the debug messages set it to True
# ─────────── Signal Handling ───────────

def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    global shutdown_flag
    print("\n🛑 Received interrupt signal. Shutting down gracefully...")
    shutdown_flag = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ─────────── Utility Functions ───────────

def detect_provider_from_model(model_id: str) -> str:
    """Detect provider from model ID."""
    model_lower = model_id.lower()
    
    if model_lower.startswith(('gpt-', 'text-embedding-', 'dall-e')):
        return "openai"
    elif model_lower.startswith(('claude-', 'sonnet', 'opus', 'haiku')):
        return "anthropic"
    elif model_lower.startswith(('gemini-', 'text-bison', 'chat-bison')):
        return "google_genai"
    elif model_lower.startswith(('gpt-4', 'gpt-35')):
        return "azure_openai"
    else:
        return "anthropic"


def get_token_expiration_time(token_created_time: int, expires_in: int) -> str:
    """Get human-readable expiration time for token."""
    expiration_timestamp = token_created_time + expires_in
    exp_time = datetime.fromtimestamp(expiration_timestamp)
    return exp_time.strftime("%Y-%m-%d %H:%M:%S")


def is_token_expired(token_created_time: int, expires_in: int, buffer_minutes: int = 5) -> bool:
    """Check if token is expired or will expire within buffer time."""
    current_time = int(time.time())
    buffer_seconds = buffer_minutes * 60
    expiration_time = token_created_time + expires_in
    return current_time + buffer_seconds >= expiration_time


def get_user_input(prompt: str = "\n👤 You: ") -> Optional[str]:
    """Get user input with proper interrupt handling."""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Goodbye!")
        global shutdown_flag
        shutdown_flag = True
        return None


# ─────────── OAuth Handler ───────────

class OAuthRedirectHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for OAuth redirect."""
    
    def do_GET(self) -> None:
        """Handle GET request for OAuth callback."""
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        
        if "code" in query:
            code = query["code"][0]
            print(f"✅ Received auth code: {code}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful. You can close this window.</h1>")
            self.server.auth_code = code
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Missing code.</h1>")
    
    def log_message(self, format: str, *args) -> None:
        """Suppress server logs."""
        pass


# ─────────── OAuth Functions ───────────

def run_temp_server(port: int = 8123, client_id: str = "reltio_ui", auth_endpoint: Optional[str] = None) -> Optional[str]:
    """Run a temporary HTTP server to capture OAuth redirect."""
    ports_to_try = [port, 8124, 8125, 8126, 8127]
    
    for current_port in ports_to_try:
        server = None
        try:
            server = http.server.HTTPServer(('localhost', current_port), OAuthRedirectHandler)
            
            if auth_endpoint:
                auth_url = f"{auth_endpoint}?client_id={client_id}&redirect_uri=http://localhost:{current_port}/callback&response_type=code"
            else:
                auth_url = f"https://login-stg.reltio.com?client_id={client_id}&redirect_uri=http://localhost:{current_port}/callback&response_type=code"
            
            print(f"🌐 Starting OAuth server on http://localhost:{current_port}/callback ...")
            time.sleep(0.5)  # Ensure server is ready
            webbrowser.open(auth_url)
            print(f"🌐 Waiting for auth redirect...")
            
            # Use a timeout to prevent hanging
            server.timeout = 60  # 60 second timeout
            server.handle_request()
            return getattr(server, "auth_code", None)
            
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {current_port} is busy, trying next port...")
                if server:
                    try:
                        server.server_close()
                    except:
                        pass
                continue
            else:
                print(f"❌ Server error: {e}")
                return None
        except KeyboardInterrupt:
            print("\n🛑 OAuth process interrupted by user")
            return None
        except Exception as e:
            print(f"❌ Error in OAuth server: {e}")
            return None
        finally:
            if server:
                try:
                    server.server_close()
                except:
                    pass
    
    print(f"❌ Could not find an available port. Tried: {ports_to_try}")
    return None


def fetch_oauth_metadata(base_url: str) -> Tuple[bool, Any]:
    """Fetch OAuth metadata from the well-known endpoint."""
    try:
        domain = base_url.replace('/ai/tools/mcp/', '')
        oauth_url = f"{domain}/ai/tools/.well-known/oauth-authorization-server"
        
        print(f"🔍 Fetching OAuth metadata from: {oauth_url}")
        response = requests.get(oauth_url, timeout=30)
        
        if response.status_code == 200:
            metadata = response.json()
            print(f"✅ OAuth metadata fetched successfully")
            return True, metadata
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


def exchange_code_for_token(
    token_endpoint: str,
    auth_code: str,
    client_id: str,
    client_secret: str
) -> Tuple[bool, Any]:
    """Exchange authorization code for access token."""
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
    }
    
    try:
        print(f"🔄 Exchanging auth code for token at: {token_endpoint}")
        response = requests.post(token_endpoint, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Access token obtained successfully")
            return True, token_data
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


# ─────────── Reltio MCP Client ───────────

class ReltioMcpClient:
    """Client for Reltio MCP server with OAuth authentication."""
    
    def __init__(self, mcp_url: str, client_id: str, client_secret: str):
        self.mcp_url = mcp_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_created_time: Optional[int] = None
        self.expires_in: Optional[int] = None
        self.token_endpoint: Optional[str] = None
        self.authorization_endpoint: Optional[str] = None
        self.oauth_metadata: Optional[Dict[str, Any]] = None
        
    def authenticate(self) -> bool:
        """Perform OAuth authentication flow."""
        print(f"🔐 Starting OAuth authentication for: {self.mcp_url}")
        
        success, metadata = fetch_oauth_metadata(self.mcp_url)
        if not success:
            print(f"❌ Failed to fetch OAuth metadata: {metadata}")
            return False
            
        self.oauth_metadata = metadata
        self.authorization_endpoint = metadata.get("authorization_endpoint")
        self.token_endpoint = metadata.get("token_endpoint")
        
        if not self.authorization_endpoint or not self.token_endpoint:
            print(f"❌ Missing required OAuth endpoints in metadata")
            return False
            
        print(f"📍 Authorization endpoint: {self.authorization_endpoint}")
        print(f"📍 Token endpoint: {self.token_endpoint}")
        
        return self._perform_authentication()
    
    def _perform_authentication(self) -> bool:
        """Perform the actual authentication steps."""
        auth_code = run_temp_server(client_id=self.client_id, auth_endpoint=self.authorization_endpoint)
        if not auth_code:
            print(f"❌ Failed to obtain authorization code")
            return False
            
        success, token_data = exchange_code_for_token(
            self.token_endpoint, auth_code, self.client_id, self.client_secret
        )
        if not success:
            print(f"❌ Failed to exchange code for token: {token_data}")
            return False
            
        self.access_token = token_data.get("access_token")
        self.expires_in = token_data.get("expires_in")
        self.token_created_time = int(time.time())
        
        if not self.access_token:
            print(f"❌ No access token in response")
            return False
            
        if not self.expires_in:
            print(f"⚠️ No expires_in in token response")
            self.expires_in = 3600  # Default to 1 hour if not provided
            
        exp_time = get_token_expiration_time(self.token_created_time, self.expires_in)
        print(f"⏰ Token expires at: {exp_time}")
        print(f"⏰ Token expires in: {self.expires_in} seconds")
        print(f"✅ Authentication successful!")
        return True
    
    def validate_and_refresh_token(self) -> bool:
        """Validate token and refresh if needed."""
        if not self.access_token or not self.token_created_time or not self.expires_in:
            print("🔐 No access token available. Starting authentication...")
            return self.authenticate()
        
        if is_token_expired(self.token_created_time, self.expires_in):
            print("⏰ Token has expired. Starting re-authentication...")
            return self.authenticate()
        
        exp_time = get_token_expiration_time(self.token_created_time, self.expires_in)
        print(f"✅ Token is valid until: {exp_time}")
        return True
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if self.validate_and_refresh_token():
            return self.access_token
        return None


# ─────────── Chat Bot ───────────

class ChatBot:
    """Interactive chat bot for Reltio MCP interactions."""
    
    def __init__(self, agent, mcp_client: ReltioMcpClient, max_history: int = 20):
        self.agent = agent
        self.mcp_client = mcp_client
        self.message_history: deque = deque(maxlen=max_history)
        self.system_message = {"role": "system", "content": SYSTEM_PROMPT}
        
    def add_message(self, message) -> None:
        """Add a message to the history."""
        self.message_history.append(message)
        
    def get_messages_for_agent(self) -> List[Dict[str, str]]:
        """Get messages in the format expected by the agent."""
        messages = [self.system_message]
        messages.extend(list(self.message_history))
        return messages
        
    async def chat_loop(self) -> None:
        """Main chat loop."""
        self._print_welcome_message()
        
        while not shutdown_flag:
            try:
                if shutdown_flag:
                    break
                    
                user_input = get_user_input()
                
                if shutdown_flag or user_input is None:
                    break
                
                if self._handle_special_commands(user_input):
                    continue
                
                if not self.mcp_client.get_valid_token():
                    print("❌ Authentication failed. Please try again.")
                    continue
                
                await self._process_user_message(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Please try again.")
        
        print("👋 Chat session ended.")
    
    def _print_welcome_message(self) -> None:
        """Print welcome message and available commands."""
        print("🤖 Reltio MCP Chat Bot")
        print("=" * 50)
        print("Type 'quit', 'exit', or 'bye' to end the conversation")
        print("Type 'clear' to clear message history")
        print("Type 'history' to see recent messages")
        print("Type 'token' to check token status")
        print("Type 'reauth' to force re-authentication")
        print("Press Ctrl+C to exit at any time")
        print("-" * 50)
    
    def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands and return True if command was handled."""
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye!")
            global shutdown_flag
            shutdown_flag = True
            return True
        elif user_input.lower() == 'clear':
            self.message_history.clear()
            print("🗑️ Message history cleared!")
            return True
        elif user_input.lower() == 'history':
            self.show_history()
            return True
        elif user_input.lower() == 'token':
            self.show_token_status()
            return True
        elif user_input.lower() == 'reauth':
            print("🔄 Forcing re-authentication...")
            if self.mcp_client.authenticate():
                print("✅ Re-authentication successful!")
            else:
                print("❌ Re-authentication failed!")
            return True
        elif not user_input:
            return True
        
        return False
    
    async def _process_user_message(self, user_input: str) -> None:
        """Process a user message and generate response."""
        user_message = HumanMessage(content=user_input)
        self.add_message(user_message)
        
        messages = self.get_messages_for_agent()
        
        print("🤖 Bot: Thinking...")
        response = await self.agent.ainvoke({"messages": messages})
        
        if "messages" in response:
            for msg in response["messages"]:
                if isinstance(msg, (AIMessage, HumanMessage, ToolMessage)):
                    self.add_message(msg)
        
        combined_response = self._combine_response_messages(response.get("messages", []))
        if combined_response:
            print(f"🤖 Bot: {combined_response}")
        else:
            print("🤖 Bot: Sorry, I couldn't generate a response.")
    
    def _combine_response_messages(self, messages: List) -> str:
        """Combine all messages from the response into a readable format."""
        if not messages:
            return ""
        
        response_parts = []
        
        for msg in messages[::-1]:
            if isinstance(msg, AIMessage):
                if msg.content:
                    if isinstance(msg.content, list):
                        combined_content = self._process_content_list(msg.content)
                        if combined_content:
                            response_parts.append(combined_content)
                    else:
                        content = str(msg.content) if msg.content else ""
                        if content:
                            response_parts.append(content)
            elif isinstance(msg, ToolMessage):
                continue
            elif isinstance(msg, HumanMessage):
                break
        
        string_parts = [str(part) for part in response_parts[::-1] if part]
        return "\n".join(string_parts) if string_parts else ""
    
    def _process_content_list(self, content_list: List) -> str:
        """Process a list of content elements and combine them intelligently."""
        if not content_list:
            return ""
        
        combined_parts = []
        
        for item in content_list:
            if isinstance(item, dict):
                if item.get('type') == 'text' and item.get('text'):
                    combined_parts.append(item['text'])
                elif item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'Unknown Tool')
                    tool_input = item.get('input', {})
                    tool_info = f"[Tool: {tool_name}] {tool_input}"
                    combined_parts.append(tool_info)
        
        return " ".join(combined_parts) if combined_parts else ""
    
    def show_history(self) -> None:
        """Show recent message history."""
        if not self.message_history:
            print("📝 No message history yet.")
            return
            
        print("\n📝 Recent Messages:")
        print("-" * 30)
        for i, msg in enumerate(self.message_history, 1):
            role_emoji, role_name = self._get_message_role_info(msg)
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"{i}. {role_emoji} {role_name}: {content}")
        print("-" * 30)
    
    def _get_message_role_info(self, msg) -> Tuple[str, str]:
        """Get emoji and role name for a message."""
        if isinstance(msg, HumanMessage):
            return "👤", "User"
        elif isinstance(msg, AIMessage):
            return "🤖", "Assistant"
        elif isinstance(msg, ToolMessage):
            return "🔧", "Tool"
        else:
            return "❓", "Unknown"
    
    def show_token_status(self) -> None:
        """Show current token status."""
        if not self.mcp_client.access_token:
            print("🔑 No access token available")
            return
        
        if not self.mcp_client.token_created_time or not self.mcp_client.expires_in:
            print("🔑 Token information incomplete")
            return
        
        exp_time = get_token_expiration_time(self.mcp_client.token_created_time, self.mcp_client.expires_in)
        is_expired = is_token_expired(self.mcp_client.token_created_time, self.mcp_client.expires_in)
        
        print("\n🔑 Token Status:")
        print("-" * 20)
        print(f"Status: {'❌ Expired' if is_expired else '✅ Valid'}")
        print(f"Expires: {exp_time}")
        print(f"Expires in: {self.mcp_client.expires_in} seconds")
        print(f"Token: {self.mcp_client.access_token[:20]}...")
        print("-" * 20)


# ─────────── Main Logic ───────────

async def main() -> None:
    """Main function to run the Reltio MCP chat bot."""
    RELTIO_MCP_SERVER = f"https://{NAMESPACE}.reltio.com/ai/tools/mcp/"
    try:
        config = {
            "RELTIO_MCP_SERVER": RELTIO_MCP_SERVER.rstrip('/') + '/',
            "RELTIO_CLIENT_ID": RELTIO_CLIENT_ID,
            "RELTIO_CLIENT_SECRET": RELTIO_CLIENT_SECRET,
            "MODEL_ID": MODEL_ID,
            "API_KEY": API_KEY
        }
        
        _print_configuration(config)
        
        provider = detect_provider_from_model(config['MODEL_ID'])
        os.environ[ENV_VAR_NAMES[provider]] = config["API_KEY"]
        
        client = ReltioMcpClient(
            config["RELTIO_MCP_SERVER"], 
            config["RELTIO_CLIENT_ID"], 
            config["RELTIO_CLIENT_SECRET"]
        )
        
        if not client.authenticate():
            print("❌ Authentication failed. Exiting.")
            return
        
        mcp_servers = {
            "reltio_server": {
                "transport": "streamable_http",
                "url": config["RELTIO_MCP_SERVER"],
                "headers": {"Authorization": f"Bearer {client.access_token}"},
            }
        }
        
        mcp_client = MultiServerMCPClient(mcp_servers)
        tools = await mcp_client.get_tools()
        print("✅ Loaded tools:", [t.name for t in tools])

        model = init_chat_model(config["MODEL_ID"],**model_configs)
        agent = create_react_agent(model, tools=tools,debug=DEBUG_MODE)
        
        chat_bot = ChatBot(agent, client)
        await chat_bot.chat_loop()
        
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("🔄 Cleaning up resources...")


def _print_configuration(config: Dict[str, str]) -> None:
    """Print configuration information."""
    print("🔧 Using Configuration:")
    print(f"   MCP Server: {config['RELTIO_MCP_SERVER']}")
    print(f"   Client ID: {config['RELTIO_CLIENT_ID']}")
    print(f"   Provider: {detect_provider_from_model(config['MODEL_ID'])}")
    print(f"   Model: {config['MODEL_ID']}")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        print("🏁 Application shutdown complete")
