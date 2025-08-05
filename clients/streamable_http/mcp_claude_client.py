
"""
This Client Example is for RELTIO ENTERPRISE MCP SERVER ONLY
"""
import asyncio
import base64
import requests
from typing import Optional
from contextlib import AsyncExitStack

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

# Constants
NAMESPACE="namepace" #reltio namspace eg test prod, etc
MODEL_NAME = "model_name" #claude-3-5-sonnet-20241022
MESSAGE_HISTORY_LIMIT = 10
CLIENT_ID ="client_id" #reltio client id
CLIENT_SECRET = "client_secret" #reltio client secret
AUTH_SERVER_URL = "https://auth.reltio.com" #reltio auth server url for prod: https://auth.reltio.com, for stg: https://auth-stg.reltio.com
API_KEY="api_key" #model api key

def get_auth_token() -> str:
    """Fetch access token using client credentials."""
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    basic_token = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    response = requests.post(f"{AUTH_SERVER_URL}/oauth/token?grant_type=client_credentials", headers=headers)
    response.raise_for_status()
    token_payload = response.json()
    return token_payload["access_token"]


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.anthropic = Anthropic(api_key=API_KEY)
        self.exit_stack = AsyncExitStack()
        self.messages = []
        self.token = get_auth_token()

    async def connect_to_streamable_http_server(self, server_url: str) -> None:
        """Establish a Streamable HTTP connection to the MCP server and initialize the client session."""
        headers = {"Authorization": f"Bearer {self.token}"}
        self._streams_context = streamablehttp_client(url=server_url, headers=headers)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()

        self._session_context = ClientSession(read_stream, write_stream)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print("Initialized Streamable HTTP client...")
        print("Connected tools:", tool_names)

    async def cleanup(self) -> None:
        """Clean up resources and exit contexts properly."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Send a query to Claude, handle any tool invocations, and return the response."""
        self.messages.append({"role": "user", "content": query})

        response = await self.session.list_tools()
        tools = [
            {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}
            for tool in response.tools
        ]

        final_text = []

        claude_response = self.anthropic.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=self.messages,
            tools=tools,
        )

        for content in claude_response.content:
            if content.type == "text":
                final_text.append(content.text)

            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                if getattr(content, "text", None):
                    self.messages.append({"role": "assistant", "content": content.text})

                self.messages.append({"role": "user", "content": result.content})

                claude_followup = self.anthropic.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1000,
                    messages=self.messages,
                )

                if claude_followup.content:
                    followup_text = claude_followup.content[0].text
                    final_text.append(followup_text)

        assistant_reply = "\n".join(final_text)
        self.messages.append({"role": "assistant", "content": assistant_reply})
        self.messages = self.messages[-MESSAGE_HISTORY_LIMIT:]

        return assistant_reply

    async def chat_loop(self) -> None:
        """Run an interactive REPL for chatting with Claude."""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as err:
                print(f"\nError: {str(err)}")


async def main():
    

    client = MCPClient()
    mcp_url=f"https://{NAMESPACE}.reltio.com/ai/tools/mcp/"
    try:
        await client.connect_to_streamable_http_server(mcp_url)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
