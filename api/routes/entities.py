"""
Entity Extraction API Routes

Endpoints for extracting teams and players from text.
"""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from api.core.entity_extraction import extract_entities


router = APIRouter(prefix="/entities", tags=["entities"])


class ExtractRequest(BaseModel):
    """Request to extract entities from text."""
    text: str


class EntityResponse(BaseModel):
    """Single entity response."""
    type: str
    name: str
    normalized_name: str
    abbreviation: str | None
    sport: str | None
    logo_url: str | None
    team_id: str | None
    player_id: str | None


class ExtractResponse(BaseModel):
    """Response with extracted entities."""
    entities: List[EntityResponse]
    count: int


@router.post("/extract", response_model=ExtractResponse)
async def extract_entities_from_text(request: ExtractRequest):
    """
    Extract sports entities (teams, players) from text.
    
    Returns a list of entities with their metadata and logo URLs.
    """
    entities = extract_entities(request.text)
    
    return ExtractResponse(
        entities=[EntityResponse(**e) for e in entities],
        count=len(entities),
    )

