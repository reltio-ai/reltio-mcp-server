"""
Tests for the main.py entry point.
"""
from unittest.mock import patch


class TestMainEntryPoint:
    """Tests for the main.py entry point."""
    
    @patch('src.server.mcp')
    @patch('dotenv.load_dotenv')
    def test_main_imports_and_setup(self, mock_load_dotenv, mock_mcp):
        """Test that main.py correctly imports and sets up the MCP server."""
        # Import main module
        import main
        
        # Verify dotenv was loaded
        mock_load_dotenv.assert_called_once()
        
        # Verify mcp is imported from server
        assert main.mcp == mock_mcp
        
    @patch('src.server.mcp')
    @patch('dotenv.load_dotenv')
    def test_main_run_not_called_on_import(self, mock_load_dotenv, mock_mcp):
        """Test that mcp.run() is not called when main is imported."""
        # Import main module
        import main
        
        # Verify mcp.run() was not called
        mock_mcp.run.assert_not_called()
        
    @patch('src.server.mcp')
    @patch('dotenv.load_dotenv')
    def test_main_run_called_when_executed_directly(self, mock_load_dotenv, mock_mcp, monkeypatch):
        """Test that mcp.run() is called when main is executed directly."""
        # Import main module after applying patches
        import importlib
        import sys
        
        # Remove main module if it's already imported
        if 'main' in sys.modules:
            del sys.modules['main']
            
        # Import main module
        import main
        
        # Call the run function directly
        main.run()
        
        # Verify mcp.run() was called with the correct transport
        mock_mcp.run.assert_called_once_with(transport="sse")
