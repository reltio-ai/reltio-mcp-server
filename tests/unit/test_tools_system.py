import pytest
from unittest.mock import patch
from src.tools.system import list_capabilities

@pytest.mark.asyncio
async def test_list_capabilities_success():
    with patch("src.tools.system.RELTIO_SERVER_NAME", "MyReltioServer"):
        result = await list_capabilities()
        
        assert isinstance(result, dict)
        assert result["server_name"] == "MyReltioServer"
        
        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert any(tool["name"] == "search_entities_tool" for tool in result["tools"])
        
        assert "prompts" in result
        assert isinstance(result["prompts"], list)
        assert result["prompts"][0]["name"] == "duplicate_review"
        
        assert "example_usage" in result
        assert isinstance(result["example_usage"], list)
        assert "get_relation_tool(relation_id='relation_id')" in result["example_usage"]
