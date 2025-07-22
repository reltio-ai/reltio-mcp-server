"""
Tests for the structure and organization of the server.py file.
"""
import inspect

# Import the server module
import src.server


class TestServerStructure:
    """Tests for the structure and organization of the server.py file."""
    
    def test_server_module_has_mcp_instance(self):
        """Test that the server module has an mcp instance."""
        assert hasattr(src.server, 'mcp')
        from mcp.server.fastmcp import FastMCP
        assert isinstance(src.server.mcp, FastMCP)
    
    def test_server_has_logger(self):
        """Test that the server module has a logger."""
        assert hasattr(src.server, 'logger')
        import logging
        assert isinstance(src.server.logger, logging.Logger)
        assert src.server.logger.name == "mcp.server.reltio"
    
    def test_all_tools_are_async_functions(self):
        """Test that all tools are async functions."""
        # Get all functions in the server module
        functions = inspect.getmembers(src.server, inspect.isfunction)
        
        # Filter for functions that are decorated with @mcp.tool()
        tool_functions = [
            func for name, func in functions 
            if name in [
                'search_entities_tool',
                'get_entity_tool',
                'update_entity_attributes_tool',
                'get_entity_matches_tool',
                'get_entity_match_history_tool',
                'get_relation_tool',
                'find_matches_by_match_score_tool',
                'find_matches_by_confidence_tool',
                'get_total_matches_tool',
                'get_total_matches_by_entity_type_tool',
                'merge_entities_tool',
                'reject_entity_match_tool',
                'export_merge_tree_tool',
                'get_business_configuration_tool',
                'get_tenant_permissions_metadata_tool',
                'capabilities_tool'
            ]
        ]
        
        # Check that all tool functions are async
        for func in tool_functions:
            assert inspect.iscoroutinefunction(func), f"{func.__name__} is not an async function"
    
    def test_all_tools_have_docstrings(self):
        """Test that all tools have docstrings."""
        # Get all functions in the server module
        functions = inspect.getmembers(src.server, inspect.isfunction)
        
        # Filter for functions that are decorated with @mcp.tool()
        tool_functions = [
            func for name, func in functions 
            if name in [
                'search_entities_tool',
                'get_entity_tool',
                'update_entity_attributes_tool',
                'get_entity_matches_tool',
                'get_entity_match_history_tool',
                'get_relation_tool',
                'find_matches_by_match_score_tool',
                'find_matches_by_confidence_tool',
                'get_total_matches_tool',
                'get_total_matches_by_entity_type_tool',
                'merge_entities_tool',
                'reject_entity_match_tool',
                'export_merge_tree_tool',
                'get_business_configuration_tool',
                'get_tenant_permissions_metadata_tool',
                'capabilities_tool'
            ]
        ]
        
        # Check that all tool functions have docstrings
        for func in tool_functions:
            assert func.__doc__ is not None, f"{func.__name__} does not have a docstring"
            assert len(func.__doc__.strip()) > 0, f"{func.__name__} has an empty docstring"
