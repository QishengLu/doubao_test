import json
import os
import sys
import time
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Add src to path to import tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import list_tables_in_directory, get_schema, query_parquet_files
from prompt.system_prompt import get_system_prompt, get_user_prompt
from tool_schemas import TOOLS

class RCAAgent:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.history: List[Dict[str, Any]] = []

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a local tool call."""
        try:
            print(f"[Agent] Executing tool: {tool_name} with args: {tool_args}")
            
            if tool_name == "list_tables_in_directory":
                directory = tool_args.get("directory", "data")
                return list_tables_in_directory(directory)
            
            elif tool_name == "get_schema":
                parquet_file = tool_args.get("parquet_file", "")
                # Handle comma-separated list
                if "," in parquet_file:
                    files = [f.strip() for f in parquet_file.split(",")]
                else:
                    files = parquet_file
                return get_schema(files)
            
            elif tool_name == "query_parquet_files":
                parquet_files = tool_args.get("parquet_files", "")
                query = tool_args.get("query", "")
                # Handle comma-separated list
                if "," in parquet_files:
                    files = [f.strip() for f in parquet_files.split(",")]
                else:
                    files = [parquet_files] if parquet_files else []
                return query_parquet_files(files, query)
            
            else:
                return f"Error: Unknown tool {tool_name}"
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"

    def call_llm_api(self, messages: List[Dict[str, Any]], use_tools: bool = True) -> Dict[str, Any]:
        """
        Call Doubao (火山方舟) API with deep thinking mode.
        """
        print("\n[System] Calling Doubao API (Deep Thinking Mode)...")
        
        # Get API Key and model configuration from environment
        api_key = os.getenv("ARK_API_KEY")
        base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        model = os.getenv("ARK_MODEL", "doubao-1-5-thinking-pro-250415")
        thinking_mode = os.getenv("ARK_THINKING_MODE", "enabled")  # enabled, disabled, auto
        
        if not api_key:
            raise ValueError("Please set ARK_API_KEY in .env")
            
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=3600
        )
        
        try:
            # Build request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "extra_body": {
                    "thinking": {
                        "type": thinking_mode
                    }
                }
            }
            
            # Add tools if enabled
            if use_tools:
                request_params["tools"] = TOOLS
                request_params["tool_choice"] = "auto"
            
            response = client.chat.completions.create(**request_params)
            
            return {
                "message": response.choices[0].message,
                "finish_reason": response.choices[0].finish_reason,
                "usage": response.usage
            }
        except Exception as e:
            raise Exception(f"API Call failed: {e}")

    def save_history(self, output_path: str = "experiments/doubao/output.json"):
        """Save the conversation history to a JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n[System] History saved to {output_path}")
        except Exception as e:
            print(f"\n[System] Error saving history: {e}")

    def run(self):
        print("Starting RCA Agent with Doubao Deep Thinking Mode...")
        print("Using local parquet tools for data analysis.")
        
        # Load prompts from prompt files
        system_prompt = get_system_prompt()
        user_prompt = get_user_prompt()
        
        # Build initial messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.history.append({"role": "system", "content": system_prompt})
        self.history.append({"role": "user", "content": user_prompt})
        
        max_iterations = 20  # Prevent infinite loops
        iteration = 0
        
        try:
            while iteration < max_iterations:
                iteration += 1
                print(f"\n[System] Iteration {iteration}/{max_iterations}")
                
                # Call LLM
                response = self.call_llm_api(messages)
                assistant_message = response["message"]
                finish_reason = response["finish_reason"]
                
                # Check if there are tool calls
                if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                    # Add assistant message to history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    self.history.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            } for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # Execute the tool
                        tool_result = self.execute_tool(tool_name, tool_args)
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                        
                        self.history.append({
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": tool_result
                        })
                        
                        print(f"[Tool Result] {tool_name}: {tool_result[:500]}...")
                else:
                    # No tool calls, this is the final response
                    final_content = assistant_message.content
                    
                    # Check for thinking content if available
                    if hasattr(assistant_message, 'reasoning_content') and assistant_message.reasoning_content:
                        print("\n[Thinking Process]")
                        print(assistant_message.reasoning_content[:2000] + "..." if len(assistant_message.reasoning_content) > 2000 else assistant_message.reasoning_content)
                    
                    print("\n" + "="*50)
                    print("Analysis Complete.")
                    print("="*50)
                    print(final_content)
                    
                    self.history.append({
                        "role": "assistant",
                        "content": final_content
                    })
                    
                    break
            
            if iteration >= max_iterations:
                print(f"\n[Warning] Reached maximum iterations ({max_iterations})")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Save history at the end of the run
        self.save_history()

if __name__ == "__main__":
    agent = RCAAgent()
    agent.run()
