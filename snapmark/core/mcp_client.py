"""MCP (Model Context Protocol) client integration for SnapMark with LLM enhancement using mcp-use."""

import asyncio
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from mcp_use import MCPAgent, MCPClient as MCPUseClient
    from langchain_openai import ChatOpenAI
    MCP_USE_AVAILABLE = True
    MCP_USE_IMPORT_ERROR = None
    # Import our custom filtered agent
    try:
        from .mcp_agent_wrapper import FilteredMCPAgent
        FILTERED_AGENT_AVAILABLE = True
    except ImportError:
        FILTERED_AGENT_AVAILABLE = False
except ImportError as e:
    MCP_USE_AVAILABLE = False
    MCP_USE_IMPORT_ERROR = str(e)
    FILTERED_AGENT_AVAILABLE = False


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    enabled: bool = True


class MCPClient:
    """Enhanced MCP client with mcp-use integration for intelligent task execution."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.logger = logging.getLogger(__name__)
        self.mcp_use_client = None
        self.mcp_agent = None
        self._load_config()
        self._initialize_mcp_use()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        await self.close()
    
    async def close(self):
        """Properly close all MCP connections and cleanup resources."""
        if self.mcp_use_client:
            try:
                # Close mcp-use client connections properly
                if hasattr(self.mcp_use_client, 'close'):
                    await self.mcp_use_client.close()
                elif hasattr(self.mcp_use_client, '_session_manager'):
                    # Close session manager and all active sessions
                    session_manager = getattr(self.mcp_use_client, '_session_manager', None)
                    if session_manager:
                        if hasattr(session_manager, 'close_all_sessions'):
                            await session_manager.close_all_sessions()
                        elif hasattr(session_manager, 'close'):
                            await session_manager.close()
                        
                        # Also check for individual sessions to close
                        if hasattr(session_manager, '_sessions'):
                            sessions = getattr(session_manager, '_sessions', {})
                            for session in sessions.values():
                                if hasattr(session, 'close'):
                                    try:
                                        await session.close()
                                    except Exception as session_e:
                                        self.logger.debug(f"Error closing individual session: {session_e}")
                
                # Wait a brief moment for sessions to close naturally
                import asyncio
                await asyncio.sleep(0.1)
                
                # Cancel any remaining pending tasks related to mcp-use
                try:
                    current_task = asyncio.current_task()
                    if current_task:
                        for task in asyncio.all_tasks():
                            if task != current_task and not task.done():
                                # Check if task is related to MCP operations
                                task_repr = str(task)
                                if any(keyword in task_repr.lower() for keyword in ['mcp', 'session', 'transport']):
                                    task.cancel()
                                    try:
                                        await asyncio.wait_for(task, timeout=0.5)
                                    except (asyncio.CancelledError, asyncio.TimeoutError):
                                        pass
                                    except Exception as task_e:
                                        self.logger.debug(f"Error cancelling MCP task: {task_e}")
                except Exception as cleanup_e:
                    self.logger.debug(f"Error during task cleanup: {cleanup_e}")
                
                self.logger.debug("mcp-use client closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing mcp-use client: {e}")
            finally:
                self.mcp_use_client = None
                self.mcp_agent = None
    
    def _initialize_mcp_use(self):
        """Initialize mcp-use client and agent if available."""
        if not MCP_USE_AVAILABLE:
            self.logger.info(f"mcp-use not available ({MCP_USE_IMPORT_ERROR}), using traditional MCP processing only")
            return
        
        try:
            # Log current MCP status
            from .mcp_requirements import log_mcp_status
            log_mcp_status()
            
            # Check if we have OpenAI configuration for LLM
            from ..config import config
            openai_config = config.get('vlm', {})
            if openai_config.get('provider') == 'openai' and openai_config.get('openai_api_key'):
                # Initialize OpenAI LLM
                llm = ChatOpenAI(
                    model=openai_config.get('openai_model', openai_config.get('model', 'gpt-4')),
                    api_key=openai_config.get('openai_api_key'),
                    temperature=0.3
                )
                
                # Get MCP config path from main config
                mcp_config_path = config.get('mcp.config_path', 'config/mcp_use_config.json')
                
                # Try to initialize mcp-use client with separate MCP config
                if Path(mcp_config_path).exists():
                    self.mcp_use_client = MCPUseClient.from_config_file(mcp_config_path)
                    # Add session options with configurable timeout to handle rate limiting
                    timeout = config.get('mcp.timeout', 120.0)
                    session_options = {"timeout": timeout}
                    
                    # Use FilteredMCPAgent if available, otherwise fallback to regular MCPAgent
                    if FILTERED_AGENT_AVAILABLE:
                        self.mcp_agent = FilteredMCPAgent(
                            llm=llm, 
                            client=self.mcp_use_client, 
                            max_steps=30,
                            # session_options=session_options
                        )
                        self.logger.info(f"✅ Successfully initialized mcp-use client with FilteredMCPAgent (image filtering enabled) with {timeout}s timeout")
                    else:
                        self.mcp_agent = MCPAgent(
                            llm=llm, 
                            client=self.mcp_use_client, 
                            max_steps=30,
                            # session_options=session_options
                        )
                        self.logger.info(f"✅ Successfully initialized mcp-use client and standard agent with {timeout}s timeout")
                else:
                    self.logger.info("⚠️  No mcp-use config file found, using basic initialization")
            else:
                self.logger.info("⚠️  OpenAI not configured, mcp-use features limited")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize mcp-use: {e}")
    
    async def run_intelligent_task(self, task_description: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run an intelligent task using mcp-use agent."""
        if not self.mcp_agent:
            return {"error": "MCP agent not available", "fallback": True}
        
        try:
            # Enhance task description with context
            if context_data:
                enhanced_task = f"{task_description}\n\nContext:\n"
                for key, value in context_data.items():
                    if isinstance(value, str) and len(value) > 200:
                        enhanced_task += f"- {key}: {value[:200]}...\n"
                    else:
                        enhanced_task += f"- {key}: {value}\n"
            else:
                enhanced_task = task_description
            
            # Run the agent
            result = await self.mcp_agent.run(enhanced_task)
            
            return {
                "success": True,
                "result": result,
                "agent_used": True
            }
            
        except Exception as e:
            self.logger.error(f"MCP agent task failed: {e}")
            return {"error": str(e), "agent_used": True}
    
    def is_agent_available(self) -> bool:
        """Check if mcp-use agent is available."""
        return self.mcp_agent is not None
    
    def _load_config(self):
        """Load MCP server configurations."""
        from ..config import config
        
        # Load from SnapMark config
        mcp_config = config.get('mcp', {})
        
        # Configuration loading info
        self.logger.info("=== MCP Configuration Loading ===")
        self.logger.info(f"MCP enabled: {mcp_config.get('enabled', False)}")
        
        if not mcp_config.get('enabled', False):
            self.logger.info("MCP is disabled, skipping server configuration")
            return
        
        servers_config = mcp_config.get('servers', {})
        self.logger.info(f"Loading {len(servers_config)} server configurations")
        
        for name, server_config in servers_config.items():
            self.logger.info(f"Processing server '{name}'")
            if isinstance(server_config, dict):
                server = MCPServerConfig(
                    name=name,
                    command=server_config.get('command', ''),
                    args=server_config.get('args', []),
                    env=server_config.get('env'),
                    enabled=server_config.get('enabled', True)
                )
                self.servers[name] = server
                self.logger.info(f"Added server '{name}': enabled={server.enabled}")
        
        self.logger.info(f"Total servers loaded: {len(self.servers)}")
        self.logger.info("=== MCP Configuration Complete ===")
    
    def is_enabled(self) -> bool:
        """Check if MCP integration is enabled."""
        from ..config import config
        return config.get('mcp.enabled', False) and len(self.servers) > 0
    
    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled MCP servers."""
        return [server for server in self.servers.values() if server.enabled]
    
    async def process_screenshot_data(self, 
                                    image_path: str, 
                                    markdown_path: str, 
                                    ocr_text: str, 
                                    vlm_description: Optional[str] = None,
                                    custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Process screenshot data through MCP servers with optional custom prompt.
        
        Args:
            image_path: Path to the screenshot image
            markdown_path: Path to the generated markdown file
            ocr_text: Extracted OCR text
            vlm_description: Optional VLM description
            custom_prompt: Optional custom prompt to guide LLM-driven MCP actions
            
        Returns:
            Dictionary with results from each MCP server
        """
        results = {}
        
        # Try mcp-use agent first if available and custom prompt provided
        if custom_prompt and self.is_agent_available():
            try:
                self.logger.info("Using mcp-use agent for intelligent processing")
                
                # Prepare context data for the agent
                context_data = {
                    "image_path": image_path,
                    "markdown_path": markdown_path,
                    "ocr_text": ocr_text,
                    "vlm_description": vlm_description,
                    "timestamp": Path(image_path).stat().st_mtime if Path(image_path).exists() else 0
                }
                
                # Run intelligent task using mcp-use agent
                agent_result = await self.run_intelligent_task(
                    custom_prompt, context_data
                )
                
                results["mcp_use_agent"] = agent_result
                
                # If agent succeeded, we can return early or continue with traditional processing
                if agent_result.get("success"):
                    self.logger.info("mcp-use agent processing completed successfully")
                    
            except Exception as e:
                self.logger.error(f"mcp-use agent processing failed: {e}")
                results["mcp_use_agent"] = {"error": str(e), "fallback_to_traditional": True}
        else:
            # Traditional MCP server processing
            enabled_servers = self.get_enabled_servers()
            
            if not enabled_servers:
                self.logger.debug("No enabled MCP servers found")
                if not results:  # Only return empty if no mcp-use results either
                    return results
            
            # Prepare data payload for MCP servers
            data_payload = {
                "image_path": image_path,
                "markdown_path": markdown_path,
                "ocr_text": ocr_text,
                "vlm_description": vlm_description,
                "custom_prompt": custom_prompt,
                "timestamp": Path(image_path).stat().st_mtime if Path(image_path).exists() else 0
            }
            
            # Process through each enabled server
            for server in enabled_servers:
                try:
                    self.logger.info(f"Processing data through MCP server: {server.name}")
                    result = await self._interact_with_server(server, data_payload)
                    results[server.name] = result
                except Exception as e:
                    self.logger.error(f"Error processing with MCP server {server.name}: {e}")
                    results[server.name] = {"error": str(e)}
        
        return results
    
    async def _interact_with_server(self, 
                                   server: MCPServerConfig, 
                                   data: Dict[str, Any]) -> Dict[str, Any]:
        """Interact with a specific MCP server."""
        try:
            # Check if it's a proper MCP server (has "stdio" in args)
            if "stdio" in server.args or server.command.endswith('-mcp-server'):
                return await self._stdio_interaction(server, data)
            else:
                # For custom server commands (like our test server)
                return await self._custom_server_interaction(server, data)
                
        except Exception as e:
            self.logger.error(f"Failed to interact with server {server.name}: {e}")
            raise
    
    async def _stdio_interaction(self, 
                               server: MCPServerConfig, 
                               data: Dict[str, Any]) -> Dict[str, Any]:
        """Interact with MCP server via stdio protocol."""
        # Build command
        cmd = [server.command] + server.args
        env = dict(server.env) if server.env else None
        
        # Execute server command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        try:
            # MCP handshake: Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "SnapMark",
                        "version": "0.1.0"
                    }
                }
            }
            
            # Send initialize request
            init_json = json.dumps(init_request) + '\n'
            process.stdin.write(init_json.encode())
            await process.stdin.drain()
            
            # Read initialize response
            init_response_line = await process.stdout.readline()
            init_response = json.loads(init_response_line.decode().strip())
            self.logger.debug(f"MCP init response: {init_response_line.decode().strip()}")
            
            # Send initialized notification (required by MCP protocol)
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            process.stdin.write((json.dumps(initialized_notification) + '\n').encode())
            await process.stdin.drain()
            
            # Now automatically process screenshot data based on server capabilities
            result = await self._process_with_available_tools(process, server, data, init_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"MCP stdio communication error: {e}")
            raise
        finally:
            try:
                process.stdin.close()
                await process.wait()
            except:
                pass
    
    async def _custom_server_interaction(self, 
                                       server: MCPServerConfig, 
                                       data: Dict[str, Any]) -> Dict[str, Any]:
        """Interact with custom MCP server implementations."""
        # For now, implement a basic subprocess call
        # This can be extended for HTTP, WebSocket, or other protocols
        
        cmd = [server.command] + server.args
        env = dict(server.env) if server.env else None
        
        # Create a temporary file with the data
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_file = f.name
        
        try:
            # Add temp file path to arguments
            cmd.append(temp_file)
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"Server command failed: {result.stderr}")
            
            # Try to parse JSON response
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"output": result.stdout, "success": True}
                
        finally:
            # Clean up temp file
            Path(temp_file).unlink(missing_ok=True)
    
    async def _process_with_available_tools(self, 
                                          process, 
                                          server: MCPServerConfig, 
                                          data: Dict[str, Any],
                                          init_response: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot data using available MCP tools."""
        try:
            # First, get available tools
            tools = await self._get_available_tools(process)
            
            if not tools:
                return {
                    "success": True,
                    "message": f"Connected to {server.name} but no tools available",
                    "tools_count": 0
                }
            
            # Process screenshot data based on available tools
            results = await self._execute_screenshot_processing(process, server, data, tools)
            
            return {
                "success": True,
                "message": f"Successfully processed screenshot data with {server.name}",
                "tools_used": len(results.get('tool_results', [])),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error processing with tools: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to process with {server.name}"
            }
    
    async def _get_available_tools(self, process) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
        try:
            # Request tools list
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            process.stdin.write((json.dumps(list_tools_request) + '\n').encode())
            await process.stdin.drain()
            
            # Read tools response
            tools_response_line = await process.stdout.readline()
            tools_response = json.loads(tools_response_line.decode().strip())
            
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                self.logger.debug(f"Found {len(tools)} available tools")
                return tools
            else:
                self.logger.warning(f"No tools found in response: {tools_response}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get available tools: {e}")
            return []
    
    async def _execute_screenshot_processing(self, 
                                           process, 
                                           server: MCPServerConfig, 
                                           data: Dict[str, Any], 
                                           tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute screenshot processing using appropriate MCP tools with LLM guidance."""
        # Get LLM-driven actions if custom prompt is provided
        llm_actions = None
        if data.get("custom_prompt"):
            llm_actions = await self._get_llm_driven_actions(data, tools)
        
        results = {
            "tool_results": [],
            "files_created": [],
            "summary": "",
            "llm_guidance": llm_actions is not None,
            "custom_prompt": data.get("custom_prompt", "")
        }
        
        # Create output directory for MCP exports
        from pathlib import Path
        export_dir = Path("SnapMarkData/excel_exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Excel filename based on screenshot (use absolute path)
        image_path = Path(data.get("image_path", ""))
        timestamp = data.get("timestamp", "unknown")
        excel_filename = f"{image_path.stem}_data.xlsx"
        excel_filepath = str(export_dir.absolute() / excel_filename)
        
        tool_id = 3  # Start tool IDs from 3 (after init and tools/list)
        
        # Step 1: Create workbook if create_workbook tool is available
        if self._has_tool(tools, "create_workbook"):
            try:
                result = await self._call_tool(process, tool_id, "create_workbook", {
                    "filepath": excel_filepath
                })
                results["tool_results"].append({"tool": "create_workbook", "result": result})
                results["files_created"].append(excel_filepath)
                tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to create workbook: {e}")
        
        # Step 2: Create additional worksheets based on LLM guidance or defaults
        if llm_actions:
            # Use LLM-recommended worksheets
            worksheets_to_create = llm_actions.get("excel_structure", {}).get("worksheets", [])
            if not worksheets_to_create:
                worksheets_to_create = ["OCR Text", "VLM Description", "Content Analysis"]
        else:
            # Default worksheets
            worksheets_to_create = ["OCR Text", "VLM Description", "Content Analysis"]
        
        if self._has_tool(tools, "create_worksheet"):
            for sheet_name in worksheets_to_create:
                try:
                    result = await self._call_tool(process, tool_id, "create_worksheet", {
                        "filepath": excel_filepath,
                        "sheet_name": sheet_name
                    })
                    results["tool_results"].append({"tool": "create_worksheet", "sheet": sheet_name, "result": result})
                    tool_id += 1
                except Exception as e:
                    self.logger.error(f"Failed to create worksheet {sheet_name}: {e}")
        
        # Step 3: Write screenshot metadata to main sheet
        if self._has_tool(tools, "write_data_to_excel"):
            try:
                # Prepare metadata
                import datetime
                metadata = [
                    ["Field", "Value"],
                    ["Timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    ["Image Path", data.get("image_path", "")],
                    ["Markdown Path", data.get("markdown_path", "")],
                    ["Original Timestamp", datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, (int, float)) else str(timestamp)],
                    ["OCR Text Length", len(data.get("ocr_text", ""))],
                    ["Has VLM Description", "Yes" if data.get("vlm_description") else "No"],
                    ["VLM Description Length", len(data.get("vlm_description", ""))],
                    ["Custom Prompt Used", "Yes" if data.get("custom_prompt") else "No"],
                    ["LLM Guidance Applied", "Yes" if llm_actions else "No"]
                ]
                
                result = await self._call_tool(process, tool_id, "write_data_to_excel", {
                    "filepath": excel_filepath,
                    "sheet_name": "Sheet",  # Default sheet name
                    "data": metadata,
                    "start_cell": "A1"
                })
                results["tool_results"].append({"tool": "write_data_to_excel", "sheet": "Screenshot Data", "result": result})
                tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to write metadata: {e}")
        
        # Step 4: Write OCR text to OCR Text sheet
        if self._has_tool(tools, "write_data_to_excel") and data.get("ocr_text"):
            try:
                ocr_data = [
                    ["OCR Text Content"],
                    [data.get("ocr_text", "")]
                ]
                
                result = await self._call_tool(process, tool_id, "write_data_to_excel", {
                    "filepath": excel_filepath,
                    "sheet_name": "OCR Text",
                    "data": ocr_data,
                    "start_cell": "A1"
                })
                results["tool_results"].append({"tool": "write_data_to_excel", "sheet": "OCR Text", "result": result})
                tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to write OCR text: {e}")
        
        # Step 5: Write VLM description to VLM Description sheet
        if self._has_tool(tools, "write_data_to_excel") and data.get("vlm_description"):
            try:
                vlm_data = [
                    ["VLM Description Content"],
                    [data.get("vlm_description", "")]
                ]
                
                result = await self._call_tool(process, tool_id, "write_data_to_excel", {
                    "filepath": excel_filepath,
                    "sheet_name": "VLM Description",
                    "data": vlm_data,
                    "start_cell": "A1"
                })
                results["tool_results"].append({"tool": "write_data_to_excel", "sheet": "VLM Description", "result": result})
                tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to write VLM description: {e}")
        
        # Step 6: Create content analysis (enhanced with LLM guidance)
        if self._has_tool(tools, "write_data_to_excel"):
            try:
                # Analyze content and extract key information
                if llm_actions:
                    # Use LLM-guided analysis
                    analysis_data = await self._create_llm_guided_analysis(data, llm_actions)
                else:
                    # Use default analysis
                    analysis_data = self._analyze_screenshot_content(data)
                
                result = await self._call_tool(process, tool_id, "write_data_to_excel", {
                    "filepath": excel_filepath,
                    "sheet_name": "Content Analysis",
                    "data": analysis_data,
                    "start_cell": "A1"
                })
                results["tool_results"].append({"tool": "write_data_to_excel", "sheet": "Content Analysis", "result": result})
                tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to write content analysis: {e}")
        
        # Step 7: Apply formatting to make the Excel file more readable
        if self._has_tool(tools, "format_range"):
            try:
                # Format headers in each sheet
                sheets_to_format = ["Sheet", "OCR Text", "VLM Description", "Content Analysis"]
                for sheet_name in sheets_to_format:
                    result = await self._call_tool(process, tool_id, "format_range", {
                        "filepath": excel_filepath,
                        "sheet_name": sheet_name,
                        "start_cell": "A1",
                        "end_cell": "Z1",  # Format entire first row
                        "bold": True,
                        "bg_color": "366092",
                        "font_color": "FFFFFF"
                    })
                    results["tool_results"].append({"tool": "format_range", "sheet": sheet_name, "result": result})
                    tool_id += 1
            except Exception as e:
                self.logger.error(f"Failed to format headers: {e}")
        
        # Update summary with LLM guidance info
        llm_info = " (with LLM guidance)" if llm_actions else ""
        results["summary"] = f"Successfully processed screenshot data{llm_info} and created Excel file with {len(results['tool_results'])} operations"
        
        return results
    
    async def _get_llm_driven_actions(self, data: Dict[str, Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to determine what actions to take based on custom prompt and available tools."""
        try:
            from ..core.vlm import VLMProcessor
            
            # Initialize VLM processor
            vlm = VLMProcessor()
            
            # Build context for LLM
            tool_names = [tool['name'] for tool in tools]
            context = f"""
You are an AI assistant helping to process screenshot data using Excel MCP tools. 

Available tools: {', '.join(tool_names)}

Screenshot context:
- OCR Text: {data.get('ocr_text', '')[:500]}...
- VLM Description: {data.get('vlm_description', '')[:500]}...
- Custom Request: {data.get('custom_prompt', '')}

Based on the custom request and screenshot content, recommend specific actions using the available Excel tools.
Respond with a JSON object containing:
{{
    "recommended_actions": [
        {{
            "tool": "tool_name",
            "reasoning": "why this tool should be used",
            "priority": 1-10,
            "parameters": {{"key": "suggested values"}}
        }}
    ],
    "excel_structure": {{
        "worksheets": ["suggested worksheet names"],
        "focus_areas": ["key areas to focus on"]
    }}
}}
"""
            
            # For text-only LLM request (since we don't need image analysis here)
            if hasattr(vlm, '_describe_image_openai') and vlm.provider.value == 'openai':
                # Use OpenAI for text analysis
                response = await self._call_llm_for_actions(vlm, context)
            else:
                # Fallback to basic analysis
                response = self._get_default_actions(data, tools)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get LLM-driven actions: {e}")
            return self._get_default_actions(data, tools)
    
    async def _call_llm_for_actions(self, vlm: 'VLMProcessor', context: str) -> Dict[str, Any]:
        """Call LLM to get recommended actions."""
        try:
            import json
            
            if vlm.provider.value == 'openai' and vlm.openai_client:
                response = vlm.openai_client.chat.completions.create(
                    model=vlm.model,
                    messages=[
                        {"role": "system", "content": "You are an Excel automation expert. Always respond with valid JSON."},
                        {"role": "user", "content": context}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Clean up response and parse JSON
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3].strip()
                
                return json.loads(response_text)
            else:
                # Fallback for other providers
                return self._get_default_actions({}, [])
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return self._get_default_actions({}, [])
    
    def _get_default_actions(self, data: Dict[str, Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get default actions when LLM is not available."""
        return {
            "recommended_actions": [
                {
                    "tool": "create_workbook",
                    "reasoning": "Create Excel workbook for screenshot data",
                    "priority": 10,
                    "parameters": {}
                },
                {
                    "tool": "write_data_to_excel",
                    "reasoning": "Write screenshot metadata and content",
                    "priority": 8,
                    "parameters": {}
                }
            ],
            "excel_structure": {
                "worksheets": ["Screenshot Data", "OCR Text", "Analysis"],
                "focus_areas": ["metadata", "text_content", "visual_analysis"]
            }
        }
    
    async def _create_llm_guided_analysis(self, data: Dict[str, Any], llm_actions: Dict[str, Any]) -> List[List[str]]:
        """Create content analysis guided by LLM recommendations."""
        analysis = [
            ["Analysis Type", "Details", "Method", "LLM Guidance"]
        ]
        
        # Extract focus areas from LLM guidance
        focus_areas = llm_actions.get("excel_structure", {}).get("focus_areas", [])
        
        # Add LLM-recommended focus areas
        for area in focus_areas:
            analysis.append(["Focus Area", area, "LLM Recommended", "Yes"])
        
        # Analyze based on custom prompt
        custom_prompt = data.get("custom_prompt", "")
        if custom_prompt:
            # Extract key terms from custom prompt
            import re
            key_terms = re.findall(r'\b[A-Za-z]{3,}\b', custom_prompt.lower())
            key_terms = list(set(key_terms))[:5]  # Limit to 5 unique terms
            
            for term in key_terms:
                ocr_text = data.get("ocr_text", "")
                vlm_desc = data.get("vlm_description", "")
                
                found_in = []
                if term in ocr_text.lower():
                    found_in.append("OCR")
                if term in vlm_desc.lower():
                    found_in.append("VLM")
                
                if found_in:
                    analysis.append(["Custom Term", term, ", ".join(found_in), "Prompt-driven"])
        
        # Add recommended actions summary
        recommended_actions = llm_actions.get("recommended_actions", [])
        high_priority_actions = [action for action in recommended_actions if action.get("priority", 0) >= 8]
        
        if high_priority_actions:
            for action in high_priority_actions:
                analysis.append(["Recommended Action", action.get("tool", ""), action.get("reasoning", ""), f"Priority {action.get('priority', 0)}"])
        
        # Fallback to default analysis if no LLM guidance produced results
        if len(analysis) == 1:  # Only header
            default_analysis = self._analyze_screenshot_content(data)
            for row in default_analysis[1:]:  # Skip header
                analysis.append(row + ["Default Analysis"])
        
        return analysis
    
    def _has_tool(self, tools: List[Dict[str, Any]], tool_name: str) -> bool:
        """Check if a specific tool is available."""
        return any(tool.get("name") == tool_name for tool in tools)
    
    async def _call_tool(self, process, tool_id: int, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific MCP tool."""
        try:
            # Create tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "id": tool_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send request
            process.stdin.write((json.dumps(tool_request) + '\n').encode())
            await process.stdin.drain()
            
            # Read response
            response_line = await process.stdout.readline()
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                self.logger.error(f"Tool {tool_name} returned error: {response['error']}")
                return {"error": response["error"]}
            
            return response.get("result", {})
            
        except Exception as e:
            self.logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}
    
    def _analyze_screenshot_content(self, data: Dict[str, Any]) -> List[List[str]]:
        """Analyze screenshot content and extract key information."""
        analysis = [
            ["Content Type", "Details", "Source"]
        ]
        
        ocr_text = data.get("ocr_text", "")
        vlm_description = data.get("vlm_description", "")
        
        # Analyze OCR text for common patterns
        if ocr_text:
            # Look for URLs
            import re
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ocr_text)
            for url in urls:
                analysis.append(["URL", url, "OCR"])
            
            # Look for email addresses
            emails = re.findall(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', ocr_text)
            for email in emails:
                analysis.append(["Email", email, "OCR"])
            
            # Look for common technology terms
            tech_terms = ["API", "HTML", "CSS", "JavaScript", "Python", "React", "Vue", "Angular", "Node.js", 
                         "Docker", "Kubernetes", "AWS", "Azure", "GCP", "database", "SQL", "JSON", "XML"]
            for term in tech_terms:
                if term.lower() in ocr_text.lower():
                    analysis.append(["Technology", term, "OCR"])
        
        # Analyze VLM description for content insights
        if vlm_description:
            # Extract key phrases from VLM description
            if "browser" in vlm_description.lower() or "chrome" in vlm_description.lower():
                analysis.append(["Application", "Web Browser", "VLM"])
            
            if "code" in vlm_description.lower() or "programming" in vlm_description.lower():
                analysis.append(["Content Type", "Code/Programming", "VLM"])
            
            if "dashboard" in vlm_description.lower() or "interface" in vlm_description.lower():
                analysis.append(["Content Type", "User Interface", "VLM"])
        
        # If no specific analysis found, add general content info
        if len(analysis) == 1:  # Only header row
            if ocr_text:
                analysis.append(["Text Content", f"OCR extracted {len(ocr_text)} characters", "OCR"])
            if vlm_description:
                analysis.append(["Visual Content", "Screenshot analyzed by vision model", "VLM"])
        
        return analysis
    
    def add_server(self, server_config: MCPServerConfig):
        """Add an MCP server configuration."""
        self.servers[server_config.name] = server_config
    
    def remove_server(self, name: str):
        """Remove an MCP server configuration."""
        if name in self.servers:
            del self.servers[name]
    
    def list_servers(self) -> List[str]:
        """List all configured MCP server names."""
        return list(self.servers.keys())
