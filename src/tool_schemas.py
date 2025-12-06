# Tool schemas for the RCA Agent
# These are imported by both rca_agent.py and mcp_server.py

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables_in_directory",
            "description": "List all parquet files in the specified directory with metadata including filename, path, row count, and column count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory path to search for parquet files. Default is 'data'."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "Get the schema (column names and types) of one or more parquet files, including row count and column information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parquet_file": {
                        "type": "string",
                        "description": "The path to the parquet file or a comma-separated list of paths."
                    }
                },
                "required": ["parquet_file"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_parquet_files",
            "description": "Execute SQL queries on parquet files. The parquet files are registered as views using their filenames (without extension) as table names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parquet_files": {
                        "type": "string",
                        "description": "Comma-separated list of parquet file paths to query."
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute. Use the filename (without .parquet extension) as the table name."
                    }
                },
                "required": ["parquet_files", "query"]
            }
        }
    }
]
