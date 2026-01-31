"""
Marketing API Routes

Endpoints for the marketing agent with streaming support.
Provides email management, X posting, and user targeting capabilities.

Authentication: API key required (X-API-Key header)
"""
import os
import json
import time
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.core.marketing_agent import (
    get_marketing_session,
    create_marketing_session,
    delete_marketing_session,
    MarketingSession,
)
from api.core.graph_email import get_graph_email_client, GraphAPIError
from api.core.user_segments import get_user_segments_client


router = APIRouter(prefix="/marketing", tags=["marketing"])


# =============================================================================
# AUTHENTICATION
# =============================================================================

MARKETING_API_KEY = os.getenv("MARKETING_API_KEY")


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify the API key for marketing endpoints."""
    if MARKETING_API_KEY:
        if not x_api_key or x_api_key != MARKETING_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new marketing session."""
    model: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response with new session details."""
    session_id: str
    created_at: str
    model: Optional[str]


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str


class ChatResponse(BaseModel):
    """Response with chat message (non-streaming)."""
    session_id: str
    response: str
    message_count: int
    tools_used: List[str] = []


class SendEmailRequest(BaseModel):
    """Request to send an email directly (no agent)."""
    to: List[str]
    subject: str
    body: str
    html: bool = True


class SendEmailResponse(BaseModel):
    """Response for email send."""
    status: str
    sent_to: List[str]
    subject: str
    sent_at: str


# =============================================================================
# SESSION ENDPOINTS
# =============================================================================

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Create a new marketing agent session.
    
    Returns a session_id that should be used for subsequent messages.
    """
    await verify_api_key(x_api_key)
    
    if request is None:
        request = CreateSessionRequest()
    
    session = create_marketing_session(model=request.model)
    
    return CreateSessionResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        model=session.model,
    )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Get marketing session details."""
    await verify_api_key(x_api_key)
    
    session = get_marketing_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Delete a marketing session."""
    await verify_api_key(x_api_key)
    
    if delete_marketing_session(session_id):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Send a message to the marketing agent (non-streaming).
    
    For streaming responses, use the /stream endpoint instead.
    """
    await verify_api_key(x_api_key)
    
    session = get_marketing_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    response = await session.chat(request.message)
    
    return ChatResponse(
        session_id=session_id,
        response=response,
        message_count=len(session.messages),
        tools_used=session.last_tools_used,
    )


@router.post("/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Send a message and stream the response via Server-Sent Events (SSE).
    
    The response is streamed as text/event-stream with each chunk
    as a data event. At the end, a 'tools' event is sent with the list
    of tools used during the response.
    """
    await verify_api_key(x_api_key)
    
    session = get_marketing_session(session_id)
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
            
            # Send tools used event before done
            if session.last_tools_used:
                tools_json = json.dumps(session.last_tools_used)
                yield f"event: tools\ndata: {tools_json}\n\n"
            
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


# =============================================================================
# DIRECT ACTION ENDPOINTS (no agent)
# =============================================================================

@router.get("/inbox")
async def get_inbox(
    limit: int = 10,
    unread_only: bool = False,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get marketing inbox summary and recent messages.
    
    This is a direct API call without using the agent.
    """
    await verify_api_key(x_api_key)
    
    try:
        client = get_graph_email_client()
        summary = await client.get_inbox_summary()
        return summary
    except GraphAPIError as e:
        raise HTTPException(status_code=500, detail=f"Graph API error: {e.message}")
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Send a marketing email directly (no agent).
    
    Use this for programmatic email sending without agent involvement.
    """
    await verify_api_key(x_api_key)
    
    if not request.to:
        raise HTTPException(status_code=400, detail="At least one recipient required")
    
    try:
        client = get_graph_email_client()
        await client.send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
            html=request.html,
        )
        
        from datetime import datetime, timezone
        return SendEmailResponse(
            status="success",
            sent_to=request.to,
            subject=request.subject,
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
    except GraphAPIError as e:
        raise HTTPException(status_code=500, detail=f"Graph API error: {e.message}")
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/segments")
async def get_segments(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get available user segments for targeting.
    
    Returns groups, tier breakdown, and total counts.
    """
    await verify_api_key(x_api_key)
    
    try:
        client = get_user_segments_client()
        summary = await client.get_segment_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/segments/{segment_type}/{segment_value}")
async def get_segment_users(
    segment_type: str,
    segment_value: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get users in a specific segment.
    
    Segment types:
    - group: Get users by group name (e.g., "beta_testers")
    - tier: Get users by tier (e.g., "pro")
    - active: Get users active in last N days (e.g., "7")
    """
    await verify_api_key(x_api_key)
    
    try:
        client = get_user_segments_client()
        
        if segment_type == "group":
            users = await client.get_users_by_group(segment_value)
        elif segment_type == "tier":
            users = await client.get_users_by_tier(segment_value)
        elif segment_type == "active":
            days = int(segment_value) if segment_value.isdigit() else 7
            users = await client.get_active_users(days)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown segment type: {segment_type}. Use 'group', 'tier', or 'active'."
            )
        
        return {
            "segment_type": segment_type,
            "segment_value": segment_value,
            "user_count": len(users),
            "users": users,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# QUICK CHAT ENDPOINTS
# =============================================================================

class QuickChatRequest(BaseModel):
    """Request for quick one-off marketing chat."""
    message: str
    model: Optional[str] = None


@router.post("/quick")
async def quick_chat(
    request: QuickChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Quick one-off marketing chat that creates a session, sends a message,
    and returns the response.
    """
    await verify_api_key(x_api_key)
    
    session = create_marketing_session(model=request.model)
    response = await session.chat(request.message)
    
    return {
        "session_id": session.session_id,
        "response": response,
        "message_count": len(session.messages),
        "tools_used": session.last_tools_used,
    }


@router.post("/quick/stream")
async def quick_chat_stream(
    request: QuickChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Quick one-off marketing chat with streaming response.
    """
    await verify_api_key(x_api_key)
    
    session = create_marketing_session(model=request.model)
    
    async def event_generator():
        """Generate SSE events from the chat stream."""
        # First send the session ID
        yield f"event: session\ndata: {session.session_id}\n\n"
        
        try:
            async for chunk in session.chat_stream(request.message):
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
            
            if session.last_tools_used:
                tools_json = json.dumps(session.last_tools_used)
                yield f"event: tools\ndata: {tools_json}\n\n"
            
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


# =============================================================================
# SCHEDULED CONTENT GENERATION
# =============================================================================

DAILY_CONTENT_PROMPTS = {
    0: "It's Monday. Check the weekend results and create a recap thread about notable outcomes, upsets, and what the results tell us about the teams involved. Post to X.",
    1: "It's Tuesday. Look at the mid-week slate (NHL/NBA focus) and create a preview thread highlighting 2-3 interesting matchups with context. Post to X.",
    2: "It's Wednesday. Find the most interesting Thursday game and create a deep-dive analysis thread. Post to X.",
    3: "It's Thursday. If there's Thursday Night Football, create an analysis thread. Otherwise, preview Friday's slate. Post to X.",
    4: "It's Friday. Create a weekend slate preview covering 2-3 games to watch across NFL/NBA/NHL with context on why they're interesting. Post to X.",
    5: "It's Saturday. Check for injury updates and line movement on tomorrow's games. Create a quick thread on what's changed. Post to X.",
    6: "It's Sunday. It's game day. Create a quick thread on the most interesting NFL matchup of the day with key numbers. Post to X.",
}


@router.post("/scheduled/daily-content")
async def generate_daily_content(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Generate and post daily content based on the posting schedule.
    Called by GitHub Actions cron job.
    """
    await verify_api_key(x_api_key)
    
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    # Get current day of week (0=Monday, 6=Sunday)
    eastern = ZoneInfo("America/New_York")
    now = datetime.now(eastern)
    day_of_week = now.weekday()
    
    prompt = DAILY_CONTENT_PROMPTS.get(day_of_week, DAILY_CONTENT_PROMPTS[4])
    
    session = create_marketing_session()
    response = await session.chat(prompt)
    
    return {
        "status": "success",
        "day": now.strftime("%A"),
        "date": now.strftime("%Y-%m-%d"),
        "prompt": prompt,
        "response": response,
        "tools_used": session.last_tools_used,
    }


# =============================================================================
# POLLING ENDPOINTS
# =============================================================================

@router.post("/poll/mentions")
async def poll_x_mentions(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Check for X @mentions and respond to them.
    Called by GitHub Actions polling job.
    
    Note: Requires X API access to fetch mentions (not yet implemented in x_posting.py).
    For now, this uses a prompt that instructs Johnny to check and respond.
    """
    await verify_api_key(x_api_key)
    
    prompt = """Check if there are any recent @mentions on X that need responses. 
    If there are mentions asking questions about games, matchups, or betting context, 
    reply with helpful, brief analysis. Remember: be helpful, don't force CTAs on every reply."""
    
    session = create_marketing_session()
    response = await session.chat(prompt)
    
    return {
        "status": "success",
        "task": "poll_mentions",
        "response": response,
        "tools_used": session.last_tools_used,
    }


@router.post("/poll/dms")
async def poll_x_dms(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Check for X DMs and respond to them.
    Called by GitHub Actions polling job.
    
    Note: Requires X API access to fetch DMs (not yet implemented in x_posting.py).
    """
    await verify_api_key(x_api_key)
    
    prompt = """Check if there are any X DMs that need responses.
    If there are DMs asking about access, invites, or questions about JohnnyBets,
    respond helpfully. For invite requests, provide instructions on how to get access."""
    
    session = create_marketing_session()
    response = await session.chat(prompt)
    
    return {
        "status": "success",
        "task": "poll_dms",
        "response": response,
        "tools_used": session.last_tools_used,
    }


@router.post("/poll/inbox")
async def poll_email_inbox(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Check the marketing inbox and respond to emails.
    Called by GitHub Actions polling job.
    """
    await verify_api_key(x_api_key)
    
    prompt = """Check the inbox for unread emails. 
    For each unread email that needs a response:
    - If it's a question about JohnnyBets, respond helpfully
    - If it's an access/invite request, provide instructions
    - If it's feedback, acknowledge it professionally
    - If it's spam or doesn't need a response, skip it
    
    Respond to any emails that need responses."""
    
    session = create_marketing_session()
    response = await session.chat(prompt)
    
    return {
        "status": "success",
        "task": "poll_inbox",
        "response": response,
        "tools_used": session.last_tools_used,
    }
