"""
This Client Example is for RELTIO ENTERPRISE MCP SERVER ONLY
"""
import asyncio
import os
import base64
import requests
from typing import Deque, List, Optional
from contextlib import AsyncExitStack
from collections import deque

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from google import genai
from google.genai import types

# Constants
MODEL_NAME: str = "gemini-2.0-flash" #model name
MESSAGE_HISTORY_LIMIT = 10 #message history limit
CLIENT_ID ="client_id" #reltio client id
CLIENT_SECRET ="client_secret" #reltio client secret
TOKEN_URL = "https://auth.reltio.com" #reltio auth server url for prod: https://auth.reltio.com, for stg: https://auth-stg.reltio.com
NAMESPACE = "namespace" #reltio namespace eg test prod, etc
MCP_SERVER_URL = f"https://{NAMESPACE}.reltio.com/ai/tools/mcp/" # Full URL like https://<ns>.reltio.com/ai/tools/mcp/
GOOGLE_API_KEY = "MODEL_API_KEY" #model api key


def get_auth_token() -> str:
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    basic_token = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    response = requests.post(f"{TOKEN_URL}/oauth/token?grant_type=client_credentials", headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]


class MCPChatClient:
    def __init__(self) -> None:
        self._streams_ctx: Optional[AsyncExitStack] = None
        self._session_ctx: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

        self.token = get_auth_token()
        self.gemini = genai.Client(api_key=GOOGLE_API_KEY)
        self.history: Deque[types.Content] = deque(maxlen=MESSAGE_HISTORY_LIMIT)

    async def connect(self, server_url: str = MCP_SERVER_URL) -> None:
        headers = {"Authorization": f"Bearer {self.token}"}
        self._streams_ctx = streamablehttp_client(url=server_url, headers=headers)
        read_stream, write_stream, _ = await self._streams_ctx.__aenter__()

        self._session_ctx = ClientSession(read_stream, write_stream)
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()

        tools = (await self.session.list_tools()).tools
        print(f"Connected to MCP server; available tools: {[tool.name for tool in tools]}")

    async def cleanup(self) -> None:
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._streams_ctx:
            await self._streams_ctx.__aexit__(None, None, None)

    def _filter_tool_schema(self, tool: types.Tool) -> types.Tool:
        schema_keys = list(types.Schema.model_fields.keys())
        if not hasattr(tool, 'inputSchema') or not tool.inputSchema or 'properties' not in tool.inputSchema:
            return tool

        def filter_nested_dict(d):
            if not isinstance(d, dict):
                return
            keys_to_remove = [k for k in d.keys() if k not in schema_keys]
            for k in keys_to_remove:
                d.pop(k, None)
            for key, value in d.items():
                if isinstance(value, dict):
                    filter_nested_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            filter_nested_dict(item)

        props = tool.inputSchema.get("properties", {})
        for key, value in props.items():
            if isinstance(value, dict):
                filter_nested_dict(value)
        return tool

    async def process(self, user_query: str) -> str:
        assert self.session, "MCP session not initialized"
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_query)]))

        tools = (await self.session.list_tools()).tools
        filtered_tools = [self._filter_tool_schema(tool) for tool in tools]
        gemini_tools: List[types.Tool] = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema
                )
            ]) for tool in filtered_tools
        ]

        config = types.GenerateContentConfig(tools=gemini_tools)
        contents = list(self.history)
        base_response = self.gemini.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )

        candidate = base_response.candidates[0]
        response_text = ""

        for part in candidate.content.parts:
            function_call = part.function_call
            if function_call:
                response_text += f"\nCalling tool: {function_call.name} with args: {function_call.args}\n"
                result = await self.session.call_tool(function_call.name, function_call.args)
                self.history.append(types.Content(
                    role="assistant",
                    parts=[types.Part(function_call=function_call)]
                ))
                result_part = types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": result},
                )
                self.history.append(types.Content(role="model", parts=[result_part]))

                final_resp = self.gemini.models.generate_content(
                    model=MODEL_NAME,
                    contents=list(self.history),
                    config=config,
                )
                response_text += final_resp.candidates[0].content.parts[0].text or ""
            else:
                response_text += part.text or ""

        self.history.append(types.Content(role="model", parts=[types.Part(text=response_text)]))
        return response_text

    async def chat_loop(self) -> None:
        print("Starting chat session (type 'quit' to exit)\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit"):
                break
            try:
                answer = await self.process(user_input)
                print(f"Assistant: {answer}\n")
            except AssertionError as ae:
                print(f"Configuration error: {ae}")
                break
            except Exception as exc:
                print(f"Error processing query: {exc}")


async def main() -> None:
    client = MCPChatClient()
    try:
        await client.connect()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
