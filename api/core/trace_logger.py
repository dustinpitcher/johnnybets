"""
Conversation Trace Logger

Logs conversation traces to Azure Blob Storage for beta monitoring and analysis.
Falls back to local file storage if Azure is not configured.
"""
import os
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4
from pathlib import Path


class ConversationLogger:
    """
    Logs conversation traces to Azure Blob Storage or local files.
    
    Each trace includes:
    - Session metadata (model, reasoning)
    - User input and assistant response
    - Tool calls with timing
    - Performance metrics
    """
    
    def __init__(self):
        self.enabled = os.getenv("TRACE_LOGGING_ENABLED", "true").lower() == "true"
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("TRACE_CONTAINER_NAME", "conversations")
        self.local_trace_dir = Path(os.getenv("LOCAL_TRACE_DIR", "./traces"))
        
        # Lazy-load blob client
        self._blob_service_client = None
        self._container_client = None
        
    def _get_blob_client(self):
        """Get or create the blob service client."""
        if self._blob_service_client is None and self.connection_string:
            try:
                from azure.storage.blob import BlobServiceClient
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                self._container_client = self._blob_service_client.get_container_client(
                    self.container_name
                )
            except ImportError:
                print("[TraceLogger] azure-storage-blob not installed, using local files")
                self._blob_service_client = False  # Mark as unavailable
            except Exception as e:
                print(f"[TraceLogger] Failed to connect to Azure Blob Storage: {e}")
                self._blob_service_client = False
        return self._container_client
    
    def _build_trace(
        self,
        session_id: str,
        user_input: str,
        response: str,
        tools_used: List[str],
        model: Optional[str],
        reasoning: Optional[str],
        latency_ms: int,
        tool_latencies: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Build the trace document."""
        trace_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Build tool calls array
        tool_calls = []
        for tool_name in tools_used:
            tool_call = {"name": tool_name}
            if tool_latencies and tool_name in tool_latencies:
                tool_call["latency_ms"] = tool_latencies[tool_name]
            tool_calls.append(tool_call)
        
        return {
            "trace_id": trace_id,
            "timestamp": timestamp.isoformat(),
            "session_id": session_id,
            "model": model,
            "reasoning": reasoning,
            "user_input": user_input,
            "assistant_response": response,
            "tool_calls": tool_calls,
            "metrics": {
                "total_latency_ms": latency_ms,
                "tool_call_count": len(tools_used),
                "response_length": len(response),
                "input_length": len(user_input),
            }
        }
    
    def _get_blob_path(self, trace_id: str) -> str:
        """Generate date-partitioned blob path."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{date_str}/{trace_id}.json"
    
    async def _upload_to_blob(self, trace: Dict[str, Any]) -> bool:
        """Upload trace to Azure Blob Storage."""
        container_client = self._get_blob_client()
        if not container_client:
            return False
        
        try:
            blob_path = self._get_blob_path(trace["trace_id"])
            blob_client = container_client.get_blob_client(blob_path)
            
            # Upload asynchronously using run_in_executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: blob_client.upload_blob(
                    json.dumps(trace, indent=2),
                    overwrite=True
                )
            )
            
            print(f"[TraceLogger] Uploaded trace to blob: {blob_path}")
            return True
            
        except Exception as e:
            print(f"[TraceLogger] Failed to upload to blob: {e}")
            return False
    
    async def _save_to_local(self, trace: Dict[str, Any]) -> bool:
        """Save trace to local file system."""
        try:
            # Create date-partitioned directory
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            trace_dir = self.local_trace_dir / date_str
            trace_dir.mkdir(parents=True, exist_ok=True)
            
            # Write trace file
            trace_file = trace_dir / f"{trace['trace_id']}.json"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: trace_file.write_text(json.dumps(trace, indent=2))
            )
            
            print(f"[TraceLogger] Saved trace to local file: {trace_file}")
            return True
            
        except Exception as e:
            print(f"[TraceLogger] Failed to save local trace: {e}")
            return False
    
    async def log_trace(
        self,
        session_id: str,
        user_input: str,
        response: str,
        tools_used: List[str],
        model: Optional[str] = None,
        reasoning: Optional[str] = None,
        latency_ms: int = 0,
        tool_latencies: Optional[Dict[str, int]] = None
    ) -> Optional[str]:
        """
        Log a conversation trace.
        
        Args:
            session_id: The chat session ID
            user_input: The user's message
            response: The assistant's response
            tools_used: List of tool names that were called
            model: The LLM model used
            reasoning: The reasoning mode (high, medium, low, none)
            latency_ms: Total response time in milliseconds
            tool_latencies: Optional dict of tool name -> latency in ms
            
        Returns:
            The trace_id if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        # Build the trace document
        trace = self._build_trace(
            session_id=session_id,
            user_input=user_input,
            response=response,
            tools_used=tools_used,
            model=model,
            reasoning=reasoning,
            latency_ms=latency_ms,
            tool_latencies=tool_latencies
        )
        
        # Try to upload to blob storage, fall back to local
        if self.connection_string:
            success = await self._upload_to_blob(trace)
            if success:
                return trace["trace_id"]
        
        # Fall back to local file storage
        success = await self._save_to_local(trace)
        if success:
            return trace["trace_id"]
        
        return None


# Singleton instance
_logger: Optional[ConversationLogger] = None


def get_logger() -> ConversationLogger:
    """Get the singleton ConversationLogger instance."""
    global _logger
    if _logger is None:
        _logger = ConversationLogger()
    return _logger
