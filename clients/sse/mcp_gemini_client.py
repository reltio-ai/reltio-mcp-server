import asyncio
import os
from typing import Deque, List, Optional
from contextlib import AsyncExitStack
from collections import deque

from mcp import ClientSession
from mcp.client.sse import sse_client
from google import genai
from google.genai import types
# Constants
GOOGLE_API_KEY: str ="YOUR API_KEY"
SERVER_URL: str = "MCP Server URL" # Example: http://localhost:8000/sse
MODEL_NAME: str = "Gemini Model ID" # Example: gemini-2.0-flash


class MCPChatClient:
    """
    MCPChatClient maintains a persistent SSE connection to an MCP server,
    manages chat history, and routes tool calls through the MCP session.
    """

    def __init__(self) -> None:
        self._streams_ctx: Optional[AsyncExitStack] = None
        self._session_ctx: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

        # Initialize Gemini client

        self.gemini = genai.Client(api_key=GOOGLE_API_KEY)

        # In-memory chat history (max 5 user + 5 assistant)
        self.history: Deque[types.Content] = deque(maxlen=10)

    async def connect(self, server_url: str = SERVER_URL) -> None:
        """
        Establish an SSE connection to the MCP server and initialize the client session.
        """
        self._streams_ctx = sse_client(url=server_url)
        streams = await self._streams_ctx.__aenter__()

        self._session_ctx = ClientSession(*streams)
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()

        tools = (await self.session.list_tools()).tools
        print(f"Connected to MCP server; available tools: {[tool.name for tool in tools]}")

    async def cleanup(self) -> None:
        """
        Clean up SSE and MCP session contexts.
        """
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._streams_ctx:
            await self._streams_ctx.__aexit__(None, None, None)
    
    def _filter_tool_schema( self,tool:types.Tool) -> types.Tool:
        """
        Filter out unnecessary fields from the tool schema, handling nested dictionaries.
        
        Args:
            tool: The tool object containing an inputSchema with properties
            
        Returns:
            The tool with filtered schema properties
        """
        
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
        """
        Handle a single user query: update history, invoke Gemini, handle tool calls, and return response.
        """
        assert self.session, "MCP session not initialized"

        # Record user message
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_query)]))

        # Retrieve tool schemas from MCP and prepare function declarations
        tools = (await self.session.list_tools()).tools
        filtered_tools= [self._filter_tool_schema(tool) for tool in tools]
        gemini_tools: List[types.Tool] = []
        for tool in filtered_tools:
            fd = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema
            )
            gemini_tools.append(types.Tool(function_declarations=[fd]))

        config = types.GenerateContentConfig(tools=gemini_tools)
        contents = list(self.history)

        # First pass: let Gemini propose an answer or a function call
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
                # Execute tool via MCP
                response_text+=(f"\nCalling tool: {function_call.name} with args: {function_call.args}\n")
                result = await self.session.call_tool(
                    function_call.name, function_call.args  # type: ignore
                )
                # Record function invocation in history
                self.history.append(
                    types.Content(
                        role="assistant",
                        parts=[types.Part(function_call=function_call)],
                    )
                )
                # Provide tool result back to Gemini
                result_part = types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": result},
                )
                self.history.append(types.Content(role="model", parts=[result_part]))

                # Second pass: generate final text
                final_resp = self.gemini.models.generate_content(
                    model=MODEL_NAME,
                    contents=list(self.history),
                    config=config,
                )
                response_text+= final_resp.candidates[0].content.parts[0].text or ""
            else:
                # Direct text response
                response_text += part.text or ""

        # Record assistant's response
        self.history.append(types.Content(role="model", parts=[types.Part(text=response_text)]))
        return response_text

    async def chat_loop(self) -> None:
        """
        Launch an interactive REPL-like chat session.
        """
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
