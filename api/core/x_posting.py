"""
X/Twitter Posting Client for JohnnyBets Marketing

Provides posting functionality for the marketing agent:
- Post tweets
- Reply to tweets
- Quote tweets
- Delete tweets

Uses OAuth 1.0a User Context authentication for posting on behalf of the account.
Note: This is separate from x_search.py which uses xAI's read-only search.

Required X Developer Portal setup:
1. Create a project and app at developer.twitter.com
2. Enable OAuth 1.0a with Read and Write permissions
3. Generate Access Token and Secret for the account

Environment variables:
- X_API_KEY: API Key (Consumer Key)
- X_API_SECRET: API Secret (Consumer Secret)
- X_ACCESS_TOKEN: Access Token for the posting account
- X_ACCESS_SECRET: Access Token Secret for the posting account
"""
import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx


class XPostingClient:
    """
    X/Twitter API v2 client for posting tweets.
    
    Uses OAuth 1.0a for user context authentication, which is required
    for posting on behalf of a specific account.
    """
    
    API_BASE = "https://api.twitter.com/2"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("X_API_KEY")
        self.api_secret = api_secret or os.getenv("X_API_SECRET")
        self.access_token = access_token or os.getenv("X_ACCESS_TOKEN")
        self.access_secret = access_secret or os.getenv("X_ACCESS_SECRET")
        
        # Validate required credentials
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            raise ValueError(
                "X API credentials required. Set X_API_KEY, X_API_SECRET, "
                "X_ACCESS_TOKEN, and X_ACCESS_SECRET environment variables."
            )
    
    def _generate_oauth_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
        oauth_params: Dict[str, str],
    ) -> str:
        """Generate OAuth 1.0a signature for the request."""
        # Combine all parameters
        all_params = {**params, **oauth_params}
        
        # Sort and encode parameters
        sorted_params = sorted(all_params.items())
        param_string = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted_params
        )
        
        # Create signature base string
        base_string = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        ])
        
        # Create signing key
        signing_key = "&".join([
            urllib.parse.quote(self.api_secret, safe=""),
            urllib.parse.quote(self.access_secret, safe=""),
        ])
        
        # Generate HMAC-SHA1 signature
        signature = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        
        return base64.b64encode(signature).decode("utf-8")
    
    def _generate_oauth_header(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate OAuth 1.0a Authorization header."""
        params = params or {}
        
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_token": self.access_token,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": base64.b64encode(os.urandom(32)).decode("utf-8").replace("=", ""),
            "oauth_version": "1.0",
        }
        
        # Generate signature
        oauth_params["oauth_signature"] = self._generate_oauth_signature(
            method, url, params, oauth_params
        )
        
        # Build Authorization header
        header_params = ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        
        return f"OAuth {header_params}"
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to X API v2."""
        url = f"{self.API_BASE}{endpoint}"
        
        headers = {
            "Authorization": self._generate_oauth_header(method, url, params or {}),
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise XAPIError(
                    status_code=response.status_code,
                    message=error_data.get("detail", response.text),
                    errors=error_data.get("errors", []),
                )
            
            return response.json()
    
    async def post_tweet(
        self,
        text: str,
        reply_to: Optional[str] = None,
        quote_tweet_id: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Post a new tweet.
        
        Args:
            text: Tweet text (max 280 characters)
            reply_to: Optional tweet ID to reply to
            quote_tweet_id: Optional tweet ID to quote
            media_ids: Optional list of media IDs to attach (from media upload)
            
        Returns:
            Dictionary with tweet ID and text
        """
        if len(text) > 280:
            raise ValueError(f"Tweet too long: {len(text)} characters (max 280)")
        
        payload: Dict[str, Any] = {"text": text}
        
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        
        if quote_tweet_id:
            payload["quote_tweet_id"] = quote_tweet_id
        
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        
        result = await self._make_request("POST", "/tweets", json_data=payload)
        
        tweet_id = result.get("data", {}).get("id")
        print(f"[XPosting] Tweet posted: {tweet_id}")
        
        return {
            "status": "success",
            "tweet_id": tweet_id,
            "text": result.get("data", {}).get("text"),
            "url": f"https://x.com/i/web/status/{tweet_id}",
        }
    
    async def delete_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """
        Delete a tweet.
        
        Args:
            tweet_id: ID of the tweet to delete
            
        Returns:
            Success status
        """
        result = await self._make_request("DELETE", f"/tweets/{tweet_id}")
        return {
            "status": "success" if result.get("data", {}).get("deleted") else "failed",
            "tweet_id": tweet_id,
        }
    
    async def post_thread(self, tweets: List[str]) -> List[Dict[str, Any]]:
        """
        Post a thread of tweets.
        
        Args:
            tweets: List of tweet texts (each max 280 characters)
            
        Returns:
            List of posted tweet data
        """
        if not tweets:
            raise ValueError("Thread must contain at least one tweet")
        
        results = []
        reply_to = None
        
        for i, text in enumerate(tweets):
            result = await self.post_tweet(text, reply_to=reply_to)
            results.append(result)
            reply_to = result["tweet_id"]
            
            # Small delay between tweets to avoid rate limiting
            if i < len(tweets) - 1:
                await asyncio.sleep(1)
        
        return results
    
    async def get_me(self) -> Dict[str, Any]:
        """Get information about the authenticated user."""
        result = await self._make_request("GET", "/users/me")
        return result.get("data", {})
    
    async def get_mentions(self, limit: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent @mentions of the authenticated user.
        
        Args:
            limit: Maximum number of mentions to return (default 10, max 100)
            since_id: Only return mentions after this tweet ID
            
        Returns:
            List of mention tweets with id, text, author, created_at
        """
        # First get our user ID
        me = await self.get_me()
        user_id = me.get("id")
        
        if not user_id:
            raise XAPIError(400, "Could not get authenticated user ID", [])
        
        params = {
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,author_id,conversation_id,in_reply_to_user_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        
        if since_id:
            params["since_id"] = since_id
        
        result = await self._make_request("GET", f"/users/{user_id}/mentions", params=params)
        
        # Map author IDs to usernames
        users = {u["id"]: u for u in result.get("includes", {}).get("users", [])}
        
        mentions = []
        for tweet in result.get("data", []):
            author = users.get(tweet.get("author_id"), {})
            mentions.append({
                "id": tweet.get("id"),
                "text": tweet.get("text"),
                "author_id": tweet.get("author_id"),
                "author_username": author.get("username"),
                "author_name": author.get("name"),
                "created_at": tweet.get("created_at"),
                "conversation_id": tweet.get("conversation_id"),
                "url": f"https://x.com/{author.get('username', 'i')}/status/{tweet.get('id')}",
            })
        
        return mentions
    
    async def get_dms(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent direct messages.
        
        Note: Requires elevated access or specific DM permissions.
        
        Args:
            limit: Maximum number of DM events to return
            
        Returns:
            List of DM events with sender, text, created_at
        """
        params = {
            "dm_event.fields": "created_at,sender_id,text",
            "max_results": min(limit, 100),
        }
        
        result = await self._make_request("GET", "/dm_events", params=params)
        
        dms = []
        for event in result.get("data", []):
            dms.append({
                "id": event.get("id"),
                "sender_id": event.get("sender_id"),
                "text": event.get("text"),
                "created_at": event.get("created_at"),
                "event_type": event.get("event_type"),
            })
        
        return dms
    
    async def reply_to_tweet(self, tweet_id: str, text: str) -> Dict[str, Any]:
        """
        Reply to a specific tweet.
        
        Args:
            tweet_id: ID of the tweet to reply to
            text: Reply text (max 280 characters)
            
        Returns:
            Posted reply data
        """
        return await self.post_tweet(text, reply_to=tweet_id)


class XAPIError(Exception):
    """Exception raised for X API errors."""
    
    def __init__(self, status_code: int, message: str, errors: List[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        super().__init__(f"X API Error ({status_code}): {message}")


# Import asyncio for thread posting
import asyncio


# Singleton instance for reuse
_client: Optional[XPostingClient] = None


def get_x_posting_client() -> XPostingClient:
    """Get or create the X posting client singleton."""
    global _client
    if _client is None:
        _client = XPostingClient()
    return _client


async def reset_client():
    """Reset the client singleton (for testing or credential rotation)."""
    global _client
    _client = None
