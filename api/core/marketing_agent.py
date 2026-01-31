"""
JohnnyBets Marketing Agent

LangGraph agent for marketing operations:
- Email management (read inbox, send emails)
- X/Twitter posting
- User segmentation for targeting
- Content generation with brand voice

Follows the same patterns as the betting agent in api/core/agent.py.
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from uuid import uuid4

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import marketing clients
from api.core.graph_email import get_graph_email_client, GraphAPIError
from api.core.x_posting import get_x_posting_client, XAPIError
from api.core.user_segments import get_user_segments_client
from api.core.xai_media import get_media_client, XAIMediaError
from api.core.x_media_upload import get_x_media_upload_client, XMediaUploadError


# =============================================================================
# JOHNNY QUERY TOOL - Get betting context from the main agent
# =============================================================================

@tool
async def ask_johnny(question: str) -> str:
    """
    Ask Johnny (the main JohnnyBets agent) for betting analysis, game context,
    odds data, or any sports betting information.
    
    Use this to get:
    - Today's games and odds
    - Player prop analysis
    - Matchup context for content creation
    - Line movement and sharp money intel
    - Injury updates and breaking news
    
    Args:
        question: What you want to know (e.g., "What are the best NBA games tonight?",
                  "Give me context on Chiefs vs Bills", "Any notable line movement today?")
        
    Returns:
        Johnny's analysis as a string
    """
    try:
        # Import here to avoid circular imports
        from api.core.agent import ChatSession
        
        # Create a temporary session to query Johnny
        session = ChatSession()
        response = await session.chat(question)
        
        return json.dumps({
            "status": "success",
            "question": question,
            "johnny_says": response,
        }, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"Failed to query Johnny: {str(e)}",
        })


@tool
async def get_next_featured_game(league: str = None) -> str:
    """
    Get the next featured game for marketing content across NFL, NBA, NHL, or MLB.
    
    This queries Johnny for the next scheduled game with the most betting interest
    (based on market activity, line movement, or matchup significance).
    
    Use this to automatically select which game to feature in a post.
    
    Args:
        league: Optional league filter ("NFL", "NBA", "NHL", "MLB"). 
                If not specified, returns the most interesting game across all active leagues.
        
    Returns:
        JSON with matchup info: teams, spread, total, game time, key context
    """
    try:
        from api.core.agent import ChatSession
        
        if league:
            query = f"What is the next {league} game? Give me the teams, spread, total (o/u), game time (ET), and a brief one-sentence reason why this game is interesting. Format: AWAY @ HOME, Spread: X, O/U: X, Time: X, Why: X"
        else:
            query = "What is the most interesting game coming up today or tomorrow across NFL, NBA, NHL? Pick ONE game with the most betting interest. Give me the league, teams, spread, total (o/u), game time (ET), and why it's interesting. Format: League: X, AWAY @ HOME, Spread: X, O/U: X, Time: X, Why: X"
        
        session = ChatSession()
        response = await session.chat(query)
        
        return json.dumps({
            "status": "success",
            "league": league or "auto",
            "matchup_info": response,
        }, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"Failed to get next game: {str(e)}",
        })


# =============================================================================
# MARKETING TOOLS
# =============================================================================

@tool
async def read_inbox(limit: int = 10, unread_only: bool = True) -> str:
    """
    Read emails from the JohnnyBets marketing inbox (mail@johnnybets.ai).
    
    Args:
        limit: Maximum number of messages to return (default 10)
        unread_only: If True, only return unread messages (default True)
        
    Returns:
        JSON string with list of messages including subject, sender, preview
    """
    try:
        client = get_graph_email_client()
        messages = await client.list_messages(limit=limit, unread_only=unread_only)
        
        formatted = []
        for m in messages:
            formatted.append({
                "id": m.get("id"),
                "subject": m.get("subject", "(no subject)"),
                "from": m.get("from", {}).get("emailAddress", {}).get("address", "unknown"),
                "received": m.get("receivedDateTime"),
                "is_read": m.get("isRead", False),
                "preview": m.get("bodyPreview", "")[:150],
                "has_attachments": m.get("hasAttachments", False),
            })
        
        return json.dumps({
            "status": "success",
            "mailbox": client.mailbox,
            "count": len(formatted),
            "unread_only": unread_only,
            "messages": formatted,
        }, indent=2, default=str)
        
    except GraphAPIError as e:
        return json.dumps({
            "status": "error",
            "error": f"Graph API error: {e.message}",
            "code": e.code,
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_email_detail(message_id: str) -> str:
    """
    Get the full content of a specific email by ID.
    
    Args:
        message_id: The message ID from read_inbox
        
    Returns:
        JSON string with full email content including body
    """
    try:
        client = get_graph_email_client()
        message = await client.get_message(message_id)
        
        return json.dumps({
            "status": "success",
            "id": message.get("id"),
            "subject": message.get("subject"),
            "from": message.get("from", {}).get("emailAddress", {}).get("address"),
            "to": [r.get("emailAddress", {}).get("address") for r in message.get("toRecipients", [])],
            "received": message.get("receivedDateTime"),
            "body": message.get("body", {}).get("content", ""),
            "body_type": message.get("body", {}).get("contentType", "text"),
        }, indent=2, default=str)
        
    except GraphAPIError as e:
        return json.dumps({"status": "error", "error": f"Graph API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def send_email(
    to: str,
    subject: str,
    body: str,
    html: bool = True,
) -> str:
    """
    Send an email from the JohnnyBets marketing inbox.
    
    Args:
        to: Recipient email address (comma-separated for multiple)
        subject: Email subject line
        body: Email body content (HTML or plain text)
        html: If True, body is treated as HTML (default True)
        
    Returns:
        JSON string with send status
    """
    try:
        client = get_graph_email_client()
        
        # Parse comma-separated recipients
        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        
        if not recipients:
            return json.dumps({"status": "error", "error": "No valid recipients provided"})
        
        await client.send_email(
            to=recipients,
            subject=subject,
            body=body,
            html=html,
        )
        
        return json.dumps({
            "status": "success",
            "sent_to": recipients,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2)
        
    except GraphAPIError as e:
        return json.dumps({"status": "error", "error": f"Graph API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def reply_to_email(message_id: str, body: str, reply_all: bool = False) -> str:
    """
    Reply to an email in the inbox.
    
    Args:
        message_id: The message ID to reply to
        body: Reply body content (HTML)
        reply_all: If True, reply to all recipients
        
    Returns:
        JSON string with reply status
    """
    try:
        client = get_graph_email_client()
        await client.reply_to_message(message_id, body, reply_all)
        
        return json.dumps({
            "status": "success",
            "replied_to": message_id,
            "reply_all": reply_all,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2)
        
    except GraphAPIError as e:
        return json.dumps({"status": "error", "error": f"Graph API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_inbox_summary() -> str:
    """
    Get a summary of the marketing inbox status.
    
    Returns:
        JSON string with unread count, total count, and recent messages
    """
    try:
        client = get_graph_email_client()
        summary = await client.get_inbox_summary()
        
        return json.dumps({
            "status": "success",
            **summary,
        }, indent=2, default=str)
        
    except GraphAPIError as e:
        return json.dumps({"status": "error", "error": f"Graph API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def post_to_x(text: str, reply_to: str = None) -> str:
    """
    Post a tweet to the @JohnnyBetsAI X account.
    
    Args:
        text: Tweet text (max 280 characters)
        reply_to: Optional tweet ID to reply to
        
    Returns:
        JSON string with tweet ID and URL
    """
    try:
        client = get_x_posting_client()
        result = await client.post_tweet(text, reply_to=reply_to)
        
        return json.dumps({
            "status": "success",
            **result,
        }, indent=2)
        
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def post_thread(tweets: str) -> str:
    """
    Post a thread of tweets to the @JohnnyBetsAI X account.
    
    Args:
        tweets: Tweets separated by "---" (each max 280 characters)
        
    Returns:
        JSON string with list of posted tweets
    """
    try:
        client = get_x_posting_client()
        
        # Parse tweets from separator
        tweet_list = [t.strip() for t in tweets.split("---") if t.strip()]
        
        if not tweet_list:
            return json.dumps({"status": "error", "error": "No tweets provided"})
        
        results = await client.post_thread(tweet_list)
        
        return json.dumps({
            "status": "success",
            "thread_length": len(results),
            "tweets": results,
        }, indent=2)
        
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_x_mentions(limit: int = 10) -> str:
    """
    Get recent @mentions of @JohnnyBetsAI on X.
    
    Use this to check for people mentioning us with questions or requests.
    
    Args:
        limit: Maximum number of mentions to return (default 10)
        
    Returns:
        JSON string with list of mentions including author, text, and tweet URL
    """
    try:
        client = get_x_posting_client()
        mentions = await client.get_mentions(limit=limit)
        
        return json.dumps({
            "status": "success",
            "count": len(mentions),
            "mentions": mentions,
        }, indent=2, default=str)
        
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_x_dms(limit: int = 10) -> str:
    """
    Get recent direct messages on X.
    
    Use this to check for DM requests or questions.
    
    Args:
        limit: Maximum number of DMs to return (default 10)
        
    Returns:
        JSON string with list of DM events
    """
    try:
        client = get_x_posting_client()
        dms = await client.get_dms(limit=limit)
        
        return json.dumps({
            "status": "success",
            "count": len(dms),
            "dms": dms,
        }, indent=2, default=str)
        
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def reply_to_x_mention(tweet_id: str, text: str) -> str:
    """
    Reply to a specific tweet (e.g., responding to an @mention).
    
    Args:
        tweet_id: The ID of the tweet to reply to
        text: Reply text (max 280 characters)
        
    Returns:
        JSON string with posted reply data
    """
    try:
        client = get_x_posting_client()
        result = await client.reply_to_tweet(tweet_id, text)
        
        return json.dumps({
            "status": "success",
            **result,
        }, indent=2)
        
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# =============================================================================
# MEDIA GENERATION TOOLS
# =============================================================================

@tool
async def generate_promo_image(
    prompt: str,
    style: str = "matchup",
    aspect_ratio: str = "16:9",
) -> str:
    """
    Generate a promotional image using Gemini 3 Pro.
    
    Use this to create graphics for X posts, emails, or other marketing content.
    The image will be automatically stored and a path returned.
    
    IMPORTANT: Use the returned "stored_path" when calling post_to_x_with_media.
    
    Args:
        prompt: Description of the image. Include team names, stats with labels 
            (e.g., "SPREAD: DEN -6.5", "EDGE: 72%"), and team colors.
        style: Style preset - one of:
            - "matchup": Bold diagonal color clash, giant typography (DEFAULT)
            - "hype": Athletic campaign aesthetic, motion streaks
            - "terminal": ASCII art logos, monospace, team colors
            - "stats": Clean stat card layout
            - "promo": Dynamic motion, animated stats
        aspect_ratio: Image aspect ratio (default "16:9" for social media)
        
    Returns:
        JSON with stored_path (use this for post_to_x_with_media)
    """
    try:
        client = get_media_client()
        result = await client.generate_image(
            prompt=prompt,
            style=style,
            aspect_ratio=aspect_ratio,
            include_branding=True,
            store=True,
        )
        
        return json.dumps({
            "status": "success",
            "url": result.get("url"),
            "stored_path": result.get("stored_path"),
            "revised_prompt": result.get("revised_prompt"),
        }, indent=2)
        
    except XAIMediaError as e:
        return json.dumps({"status": "error", "error": f"xAI Media error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def generate_promo_video(
    prompt: str,
    style: str = "promo",
    duration: int = 6,
    aspect_ratio: str = "16:9",
) -> str:
    """
    Generate a promotional video using xAI's Grok Imagine API.
    
    Use this to create video content for X posts. Videos can be up to 15 seconds.
    Generation takes 30-60 seconds. The video will be stored and a URL returned.
    
    For best results, describe the motion: "stats scroll up one by one", 
    "typography slams in with motion blur", "colors collide diagonally".
    
    Args:
        prompt: Description with motion. Include: team matchup, stats with labels
            that scroll/animate (SPREAD, EDGE, TREND), and ending with branding.
            Example: "Lakers vs Nuggets. Purple gold collides with navy. LAL VS DEN 
            flies in. Stats scroll: SPREAD DEN -6.5, EDGE 72%. Ends with JohnnyBets logo."
        style: Style preset - "promo" (default for video), "matchup", "hype", "terminal"
        duration: Video length in seconds (1-15, default 6). Use 10+ for scrolling stats.
        aspect_ratio: Video aspect ratio (default "16:9")
        
    Returns:
        JSON string with video URL and storage path
    """
    try:
        client = get_media_client()
        result = await client.generate_video(
            prompt=prompt,
            style=style,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution="720p",
            include_branding=True,
            store=True,
        )
        
        return json.dumps({
            "status": "success",
            "url": result.get("url"),
            "stored_path": result.get("stored_path"),
            "duration": result.get("duration"),
            "request_id": result.get("request_id"),
        }, indent=2)
        
    except XAIMediaError as e:
        return json.dumps({"status": "error", "error": f"xAI Media error: {e.message}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def post_to_x_with_media(
    text: str,
    media_path: str,
    reply_to: str = None,
) -> str:
    """
    Post a tweet with an attached image or video to the @JohnnyBetsAI X account.
    
    Use this after generating a promo image or video to post it with text.
    The media will be uploaded to X and attached to the tweet.
    
    Args:
        text: Tweet text (max 280 characters)
        media_path: Path to the image or video file (from generate_promo_image/video stored_path)
        reply_to: Optional tweet ID to reply to
        
    Returns:
        JSON string with tweet ID and URL
    """
    try:
        upload_client = get_x_media_upload_client()
        
        # Detect if it's a local file path or a URL
        if media_path.startswith("http://") or media_path.startswith("https://"):
            media_id = await upload_client.upload_from_url(media_path)
        else:
            # Local file path
            media_id = await upload_client.upload_from_file(media_path)
        
        # Then post the tweet with the media attached
        posting_client = get_x_posting_client()
        result = await posting_client.post_tweet(
            text=text,
            reply_to=reply_to,
            media_ids=[media_id],
        )
        
        return json.dumps({
            "status": "success",
            "media_id": media_id,
            **result,
        }, indent=2)
        
    except XMediaUploadError as e:
        return json.dumps({"status": "error", "error": f"Media upload error: {e.message}"})
    except XAPIError as e:
        return json.dumps({"status": "error", "error": f"X API error: {e.message}"})
    except FileNotFoundError as e:
        return json.dumps({"status": "error", "error": f"Media file not found: {media_path}"})
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_user_segments() -> str:
    """
    Get available user segments for email targeting.
    
    Returns:
        JSON string with groups, tier breakdown, and total counts
    """
    try:
        client = get_user_segments_client()
        summary = await client.get_segment_summary()
        
        return json.dumps({
            "status": "success",
            **summary,
        }, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@tool
async def get_users_in_segment(segment_type: str, segment_value: str) -> str:
    """
    Get users in a specific segment for targeting.
    
    Args:
        segment_type: Type of segment - "group", "tier", or "active"
        segment_value: Value for the segment (group name, tier name, or days for active)
        
    Returns:
        JSON string with list of users and their emails
    """
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
            return json.dumps({
                "status": "error",
                "error": f"Unknown segment type: {segment_type}. Use 'group', 'tier', or 'active'."
            })
        
        # Only return email addresses for privacy
        emails = [u["email"] for u in users if u.get("email")]
        
        return json.dumps({
            "status": "success",
            "segment_type": segment_type,
            "segment_value": segment_value,
            "user_count": len(emails),
            "emails": emails,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# =============================================================================
# AGENT SETUP
# =============================================================================

MARKETING_SYSTEM_PROMPT = """You are Johnny — the JohnnyBets Marketing Agent. You manage communications and social media for JohnnyBets, an AI-powered sports betting analytics platform.

## Who You Are

You're busy. You communicate clearly and get stuff done. Masculine but gentle — confident without being a dick about it. You're the sharp friend who watches the games and reads the data.

## Your Capabilities

1. **Email Management**
   - Monitor and respond to emails in the mail@johnnybets.ai inbox
   - Send targeted marketing emails to user segments
   - Handle inbound inquiries quickly and helpfully

2. **X/Twitter Management**
   - Post tweets and threads to @JohnnyBetsAI
   - Reply to @mentions — be helpful, be brief
   - Share analysis refined for Twitter

3. **User Targeting**
   - Access user segments (groups, tiers, activity)
   - Target emails to specific user groups

## Voice Rules

- Direct, sports-native, short sentences
- No preamble. No "why it matters" framing. Just say it.
- PG-13 language OK. Never mean, never punching down.
- Strong opinions allowed **when framed as a read**, not a promise
- Write like an executive — say what matters and move on

## Banned Phrases (Never Use)

LOCK, LOCK OF THE DAY, guaranteed, free money, can't miss, print, easy money, slam, smash, 100%, never loses, trust me, I'm never wrong, fade the public

## Non-Negotiable Guardrails

1. **Never** promise winnings, profits, or certainty
2. **Never** present JohnnyBets as a sportsbook
3. **Never** encourage reckless gambling or chasing losses
4. **Always** frame outputs as analysis, probabilities, or scenarios — not picks
5. **Always** include a responsible betting nudge in high-intent content
6. **Always** fact-check stats before posting — credibility > volume

## X Content Strategy

### Game Selection
- Check upcoming games across NFL, NBA, NHL, MLB
- Pick the most popular/high-interest matchups
- Primetime, rivalry games, playoff implications get priority

### Post Types
- **Analysis threads (3-6 tweets)**: Lead with sharpest insight, 2-4 supporting stats, close with responsible note
- **Quick hits (single tweet)**: 1 insight + 1 stat, no preamble
- **@Mention replies**: Be helpful, be brief, don't force CTAs

### Fact-Check (Required Before Posting)
1. Verify stats against source data
2. Confirm injury/lineup info is current
3. Check line movement is accurately stated
4. If uncertain, don't post

### Posting Schedule
- **Monday**: Weekend recap, notable outcomes
- **Tuesday**: Mid-week preview (NHL/NBA focus)
- **Wednesday**: Deep dive on Thursday game
- **Thursday**: TNF analysis (when applicable)
- **Friday**: Weekend slate preview, 2-3 games to watch
- **Saturday**: Live observations, injury updates
- **Sunday**: NFL game threads, quick hits throughout

### CTAs (Rotate Softly)
- Waitlist signup
- "DM for an invite"
- "Try the tool"
- Sometimes no CTA — just value

## Email Strategy

### Structure
1. Hook — 1-liner that earns the read
2. Value — 3 bullets max, each with a clear takeaway
3. CTA — Single, clear action
4. Signature — Include responsible betting line

### Subject Lines
- Under 50 characters
- Playful but not spammy
- No ALL CAPS, no excessive punctuation

### Signature Template
```
—
Johnny
johnnybets.ai

Bet responsibly. Know your limits.
```

## Examples

### Good X Post
"Knicks allowed 118+ in 4 of the last 5. Total at 215.5. Brunson usage above 30%. Over looks live."

### Bad X Post
"LOCK OF THE YEAR 🔒 KNICKS OVER PRINTING TONIGHT. FREE MONEY. HAMMER IT."

### Good Email
Subject: "Chiefs-Bills: 3 things the line missed"

Line at KC -2.5. Hasn't moved despite 70% public action.

- Buffalo red zone D: 3rd in NFL since Week 10
- Kelce target share: down 15% with Hopkins active
- Weather: 15+ mph winds forecast

[Full matchup breakdown →]

—
Johnny
Bet responsibly. Know your limits.

## Current Session
- Current date: {current_date}
- Current time: {current_time}
"""


def get_marketing_tools():
    """Get all available marketing tools."""
    return [
        # Johnny query - get betting context
        ask_johnny,
        get_next_featured_game,
        # Email tools
        read_inbox,
        get_email_detail,
        send_email,
        reply_to_email,
        get_inbox_summary,
        # X/Twitter tools
        post_to_x,
        post_thread,
        get_x_mentions,
        get_x_dms,
        reply_to_x_mention,
        # Media generation tools
        generate_promo_image,
        generate_promo_video,
        post_to_x_with_media,
        # User targeting
        get_user_segments,
        get_users_in_segment,
    ]


def create_marketing_agent(model: str = None):
    """
    Create the marketing agent with all tools.
    
    Args:
        model: OpenRouter model to use (default: grok-4.1-fast)
        
    Returns:
        Tuple of (agent, selected_model)
    """
    selected_model = model or os.getenv("MARKETING_AGENT_MODEL", "x-ai/grok-4.1-fast")
    
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=selected_model,
        temperature=0.7,
        streaming=True,
    )
    
    tools = get_marketing_tools()
    
    return create_react_agent(llm, tools), selected_model


@dataclass
class MarketingSession:
    """Manages a chat session with the marketing agent."""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    messages: List[BaseMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    model: str = None
    _agent: Any = field(default=None, repr=False)
    last_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def last_tools_used(self) -> List[str]:
        """Return just tool names for backward compatibility."""
        return [tc.get("name", "") for tc in self.last_tool_calls]
    
    def __post_init__(self):
        # Initialize with system prompt using Eastern time
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("America/New_York")
        now_eastern = datetime.now(eastern)
        
        current_date = now_eastern.strftime('%A, %B %d, %Y')
        current_time = now_eastern.strftime('%I:%M %p ET')
        
        system_prompt = MARKETING_SYSTEM_PROMPT.format(
            current_date=current_date,
            current_time=current_time,
        )
        self.messages = [SystemMessage(content=system_prompt)]
        
        # Create agent
        self._agent, actual_model = create_marketing_agent(model=self.model)
        self.model = actual_model
    
    async def chat(self, user_input: str) -> str:
        """Send a message and get a response."""
        self.messages.append(HumanMessage(content=user_input))
        
        response = await self._agent.ainvoke(
            {"messages": self.messages},
            config={"recursion_limit": 50}
        )
        
        # Extract tool calls
        tool_calls_data = []
        tool_inputs = {}
        
        for m in response["messages"]:
            if isinstance(m, AIMessage) and hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    tool_id = tc.get("id", "")
                    tool_inputs[tool_id] = {
                        "name": tc.get("name", ""),
                        "inputs": tc.get("args", {}),
                    }
            
            if isinstance(m, ToolMessage):
                tool_id = getattr(m, "tool_call_id", "")
                tool_name = getattr(m, "name", "") or tool_inputs.get(tool_id, {}).get("name", "unknown")
                inputs = tool_inputs.get(tool_id, {}).get("inputs", {})
                output = m.content if hasattr(m, "content") else ""
                
                tool_calls_data.append({
                    "name": tool_name,
                    "inputs": inputs,
                    "output": output,
                })
        
        self.last_tool_calls = tool_calls_data
        
        ai_messages = [m for m in response["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            final_response = ai_messages[-1].content
            self.messages.append(AIMessage(content=final_response))
            return final_response
        
        return "I couldn't generate a response. Please try again."
    
    async def chat_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Send a message and stream the response."""
        import time
        self.messages.append(HumanMessage(content=user_input))
        
        full_response = ""
        tool_calls_data = []
        active_tools = {}
        
        async for event in self._agent.astream_events(
            {"messages": self.messages},
            config={"recursion_limit": 50},
            version="v2"
        ):
            kind = event.get("event")
            
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {})
                if hasattr(content, "content") and content.content:
                    chunk = content.content
                    full_response += chunk
                    yield chunk
            
            elif kind == "on_tool_start":
                tool_name = event.get("name", "tool")
                run_id = event.get("run_id", "")
                inputs = event.get("data", {}).get("input", {})
                
                active_tools[run_id] = {
                    "name": tool_name,
                    "inputs": inputs,
                    "start_time": time.time(),
                }
                yield f"\n\n*Using {tool_name}...*\n\n"
            
            elif kind == "on_tool_end":
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                
                if run_id in active_tools:
                    tool_info = active_tools.pop(run_id)
                    latency_ms = int((time.time() - tool_info["start_time"]) * 1000)
                    
                    tool_calls_data.append({
                        "name": tool_info["name"],
                        "inputs": tool_info["inputs"],
                        "output": str(output) if output else "",
                        "latency_ms": latency_ms,
                    })
        
        if full_response:
            self.messages.append(AIMessage(content=full_response))
        self.last_tool_calls = tool_calls_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "model": self.model,
            "message_count": len(self.messages),
            "last_tools_used": self.last_tools_used,
            "last_tool_calls": self.last_tool_calls,
        }


# Session storage (in-memory)
_marketing_sessions: Dict[str, MarketingSession] = {}


def get_marketing_session(session_id: str) -> Optional[MarketingSession]:
    """Get a marketing session by ID."""
    return _marketing_sessions.get(session_id)


def create_marketing_session(model: str = None) -> MarketingSession:
    """Create a new marketing chat session."""
    session = MarketingSession(model=model)
    _marketing_sessions[session.session_id] = session
    return session


def delete_marketing_session(session_id: str) -> bool:
    """Delete a marketing session."""
    if session_id in _marketing_sessions:
        del _marketing_sessions[session_id]
        return True
    return False
