"""
Tools API Routes

Endpoints for the public Tools page and tool registry management.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.core.tool_registry import (
    get_registry,
    ToolStatus,
    ToolCategory,
)


router = APIRouter(prefix="/tools", tags=["tools"])


class ToolResponse(BaseModel):
    """Single tool response."""
    id: str
    name: str
    description: str
    category: str
    status: str
    icon: str
    sports: List[str]
    function_name: Optional[str] = None
    eta: Optional[str] = None
    price_tier: Optional[str] = None
    votes: int = 0


class ToolsListResponse(BaseModel):
    """List of tools response."""
    tools: List[ToolResponse]
    total: int
    filters: dict


class VoteResponse(BaseModel):
    """Vote response."""
    success: bool
    tool_id: str
    new_vote_count: int


@router.get("", response_model=ToolsListResponse)
async def list_tools(
    status: Optional[str] = Query(None, description="Filter by status: free, premium, roadmap, idea"),
    category: Optional[str] = Query(None, description="Filter by category: general, nfl, nhl, mlb"),
    sport: Optional[str] = Query(None, description="Filter by sport: nfl, nhl, mlb, nba"),
):
    """
    List all tools with optional filters.
    
    This endpoint powers the public /tools page.
    """
    registry = get_registry()
    tools = registry.get_all_tools()
    
    # Apply filters
    if status:
        try:
            status_enum = ToolStatus(status.lower())
            tools = [t for t in tools if t.status == status_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if category:
        try:
            category_enum = ToolCategory(category.lower())
            tools = [t for t in tools if t.category == category_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    if sport:
        sport_lower = sport.lower()
        tools = [t for t in tools if sport_lower in t.sports]
    
    # Convert to response
    tool_responses = [
        ToolResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category.value,
            status=t.status.value,
            icon=t.icon,
            sports=t.sports,
            function_name=t.function_name,
            eta=t.eta,
            price_tier=t.price_tier,
            votes=t.votes,
        )
        for t in tools
    ]
    
    return ToolsListResponse(
        tools=tool_responses,
        total=len(tool_responses),
        filters={
            "status": status,
            "category": category,
            "sport": sport,
        }
    )


@router.get("/stats")
async def get_tool_stats():
    """
    Get tool statistics for dashboard display.
    """
    registry = get_registry()
    
    return {
        "total": len(registry.get_all_tools()),
        "by_status": {
            "free": len(registry.get_free_tools()),
            "premium": len(registry.get_premium_tools()),
            "roadmap": len(registry.get_roadmap_tools()),
            "idea": len(registry.get_idea_tools()),
        },
        "by_category": {
            "general": len(registry.get_tools_by_category(ToolCategory.GENERAL)),
            "nfl": len(registry.get_tools_by_category(ToolCategory.NFL)),
            "nba": len(registry.get_tools_by_category(ToolCategory.NBA)),
            "nhl": len(registry.get_tools_by_category(ToolCategory.NHL)),
            "mlb": len(registry.get_tools_by_category(ToolCategory.MLB)),
        },
        "by_sport": {
            "nfl": len(registry.get_tools_by_sport("nfl")),
            "nhl": len(registry.get_tools_by_sport("nhl")),
            "mlb": len(registry.get_tools_by_sport("mlb")),
            "nba": len(registry.get_tools_by_sport("nba")),
        }
    }


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: str):
    """
    Get a single tool by ID.
    """
    registry = get_registry()
    tool = registry.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    return ToolResponse(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        category=tool.category.value,
        status=tool.status.value,
        icon=tool.icon,
        sports=tool.sports,
        function_name=tool.function_name,
        eta=tool.eta,
        price_tier=tool.price_tier,
        votes=tool.votes,
    )


@router.post("/{tool_id}/vote", response_model=VoteResponse)
async def vote_for_tool(tool_id: str):
    """
    Vote for an idea tool.
    
    Only works for tools with status="idea".
    Future: Will require authentication.
    """
    registry = get_registry()
    tool = registry.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    if tool.status != ToolStatus.IDEA:
        raise HTTPException(
            status_code=400, 
            detail=f"Can only vote for idea tools. This tool has status: {tool.status.value}"
        )
    
    success = registry.vote_for_tool(tool_id)
    
    return VoteResponse(
        success=success,
        tool_id=tool_id,
        new_vote_count=tool.votes,
    )

