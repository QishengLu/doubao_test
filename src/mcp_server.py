import os
import sys
import json
from fastmcp import FastMCP

# Add src to path to import tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import list_tables_in_directory, get_schema, query_parquet_files
from tool_schemas import TOOLS

# Initialize FastMCP
mcp = FastMCP("RCA Data MCP Server")

@mcp.tool()
def list_tables(directory: str = "data") -> str:
    """
    List all parquet files in the specified directory with metadata.
    Returns filename, path, row count, and column count for each file.
    """
    print(f"[MCP] Listing tables in: {directory}")
    try:
        result = list_tables_in_directory(directory)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_table_schema(parquet_file: str) -> str:
    """
    Get the schema (column names and types) of a parquet file.
    Also returns row count and notes about special characters in column names.
    """
    print(f"[MCP] Getting schema for: {parquet_file}")
    try:
        result = get_schema(parquet_file)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def query_data(parquet_files: str, query: str) -> str:
    """
    Execute SQL queries on parquet files using DuckDB.
    
    Args:
        parquet_files: Comma-separated list of parquet file paths
        query: SQL query to execute. Use the filename (without .parquet) as table name.
    
    Example:
        parquet_files: "data/logs.parquet,data/metrics.parquet"
        query: "SELECT * FROM logs WHERE level = 'ERROR' LIMIT 10"
    """
    print(f"[MCP] Executing query on files: {parquet_files}")
    print(f"[MCP] Query: {query}")
    try:
        # Parse comma-separated files
        files = [f.strip() for f in parquet_files.split(",") if f.strip()]
        result = query_parquet_files(files, query)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    # Force SSE transport on port 8000
    mcp.run(transport="sse", port=8000)
