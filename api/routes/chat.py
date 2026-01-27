"""
Chat API Routes

Endpoints for the chat interface with streaming support.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.core.agent import (
    get_session,
    create_session,
    delete_session,
    ChatSession,
)


router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""
    model: Optional[str] = None
    reasoning: Optional[str] = "high"


class CreateSessionResponse(BaseModel):
    """Response with new session details."""
    session_id: str
    created_at: str
    model: Optional[str]
    reasoning: Optional[str]


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    """Response with chat message (non-streaming)."""
    session_id: str
    response: str
    message_count: int


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(request: CreateSessionRequest = None):
    """
    Create a new chat session.
    
    Returns a session_id that should be used for subsequent messages.
    """
    if request is None:
        request = CreateSessionRequest()
    
    session = create_session(model=request.model, reasoning=request.reasoning)
    
    return CreateSessionResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        model=session.model,
        reasoning=session.reasoning,
    )


@router.get("/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """
    Get session details.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """
    Delete a chat session.
    """
    if delete_session(session_id):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(session_id: str, request: ChatRequest):
    """
    Send a message to the chat agent (non-streaming).
    
    For streaming responses, use the /stream endpoint instead.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    response = await session.chat(request.message)
    
    return ChatResponse(
        session_id=session_id,
        response=response,
        message_count=len(session.messages),
    )


@router.post("/sessions/{session_id}/stream")
async def stream_message(session_id: str, request: ChatRequest):
    """
    Send a message and stream the response via Server-Sent Events (SSE).
    
    The response is streamed as text/event-stream with each chunk
    as a data event.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    async def event_generator():
        """Generate SSE events from the chat stream."""
        try:
            async for chunk in session.chat_stream(request.message):
                # Escape newlines for SSE format
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
            
            # Send done event
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# Quick chat endpoint (creates session automatically)
class QuickChatRequest(BaseModel):
    """Request for quick one-off chat."""
    message: str
    model: Optional[str] = None
    reasoning: Optional[str] = "high"


@router.post("/quick")
async def quick_chat(request: QuickChatRequest):
    """
    Quick one-off chat that creates a session, sends a message,
    and returns the response.
    
    Good for testing or single-message interactions.
    Note: Session is still stored and can be continued.
    """
    session = create_session(model=request.model, reasoning=request.reasoning)
    response = await session.chat(request.message)
    
    return {
        "session_id": session.session_id,
        "response": response,
        "message_count": len(session.messages),
    }


@router.post("/quick/stream")
async def quick_chat_stream(request: QuickChatRequest):
    """
    Quick one-off chat with streaming response.
    
    Creates a session and streams the response.
    """
    session = create_session(model=request.model, reasoning=request.reasoning)
    
    async def event_generator():
        """Generate SSE events from the chat stream."""
        # First send the session ID
        yield f"event: session\ndata: {session.session_id}\n\n"
        
        try:
            async for chunk in session.chat_stream(request.message):
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

