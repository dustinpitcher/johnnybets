"""
Microsoft Graph Email Client for JohnnyBets Marketing

Provides email functionality for the marketing agent:
- Read emails from shared mailbox (mail@johnnybets.ai)
- Send emails as the shared mailbox
- List/search inbox messages
- Mark messages as read

Uses OAuth2 client credentials flow (app-only authentication).

Required Azure App Registration permissions (Application):
- Mail.Read
- Mail.Send
- Mail.ReadWrite

Environment variables:
- GRAPH_CLIENT_ID: Azure AD app client ID
- GRAPH_CLIENT_SECRET: Azure AD app client secret
- GRAPH_TENANT_ID: Azure AD tenant ID
- MARKETING_MAILBOX: Shared mailbox email (default: mail@johnnybets.ai)
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx


class GraphEmailClient:
    """
    Microsoft Graph API client for email operations.
    
    Uses client credentials flow for app-only authentication,
    allowing access to shared mailboxes without user interaction.
    """
    
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        mailbox: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("GRAPH_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GRAPH_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.getenv("GRAPH_TENANT_ID")
        self.mailbox = mailbox or os.getenv("MARKETING_MAILBOX", "mail@johnnybets.ai")
        
        # Validate required credentials
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError(
                "Microsoft Graph credentials required. Set GRAPH_CLIENT_ID, "
                "GRAPH_CLIENT_SECRET, and GRAPH_TENANT_ID environment variables."
            )
        
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token using client credentials flow."""
        # Return cached token if still valid (with 5 min buffer)
        if self._access_token and self._token_expires:
            buffer = 300  # 5 minutes
            if datetime.now(timezone.utc).timestamp() < self._token_expires.timestamp() - buffer:
                return self._access_token
        
        token_url = self.TOKEN_URL.format(tenant_id=self.tenant_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            data = response.json()
        
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires = datetime.now(timezone.utc).replace(
            microsecond=0
        )
        self._token_expires = datetime.fromtimestamp(
            self._token_expires.timestamp() + expires_in,
            tz=timezone.utc
        )
        
        return self._access_token
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to Microsoft Graph API."""
        token = await self._get_access_token()
        
        url = f"{self.GRAPH_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
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
            
            # Handle different response types
            if response.status_code == 204:
                return {"status": "success"}
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise GraphAPIError(
                    status_code=response.status_code,
                    message=error_data.get("error", {}).get("message", response.text),
                    code=error_data.get("error", {}).get("code", "unknown"),
                )
            
            return response.json()
    
    async def list_messages(
        self,
        limit: int = 10,
        unread_only: bool = False,
        folder: str = "inbox",
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List messages from the shared mailbox.
        
        Args:
            limit: Maximum number of messages to return
            unread_only: If True, only return unread messages
            folder: Mail folder to read from (inbox, sentitems, etc.)
            search: Optional search query (OData $search)
            
        Returns:
            List of message dictionaries with id, subject, from, receivedDateTime, etc.
        """
        endpoint = f"/users/{self.mailbox}/mailFolders/{folder}/messages"
        
        params = {
            "$top": limit,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,hasAttachments",
        }
        
        if unread_only:
            params["$filter"] = "isRead eq false"
        
        if search:
            params["$search"] = f'"{search}"'
        
        result = await self._make_request("GET", endpoint, params=params)
        return result.get("value", [])
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get a single message by ID with full body.
        
        Args:
            message_id: The message ID
            
        Returns:
            Full message including body content
        """
        endpoint = f"/users/{self.mailbox}/messages/{message_id}"
        params = {
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,body,hasAttachments",
        }
        return await self._make_request("GET", endpoint, params=params)
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read."""
        endpoint = f"/users/{self.mailbox}/messages/{message_id}"
        return await self._make_request("PATCH", endpoint, json_data={"isRead": True})
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: bool = True,
        cc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email from the shared mailbox.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            html: If True, body is treated as HTML; otherwise plain text
            cc: Optional list of CC recipients
            reply_to: Optional reply-to address
            
        Returns:
            Success status
        """
        endpoint = f"/users/{self.mailbox}/sendMail"
        
        message = {
            "subject": subject,
            "body": {
                "contentType": "HTML" if html else "Text",
                "content": body,
            },
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        }
        
        if cc:
            message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
        
        if reply_to:
            message["replyTo"] = [{"emailAddress": {"address": reply_to}}]
        
        return await self._make_request("POST", endpoint, json_data={"message": message})
    
    async def reply_to_message(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Reply to an existing message.
        
        Args:
            message_id: The message to reply to
            body: Reply body content (HTML)
            reply_all: If True, reply to all recipients
            
        Returns:
            Success status
        """
        action = "replyAll" if reply_all else "reply"
        endpoint = f"/users/{self.mailbox}/messages/{message_id}/{action}"
        
        return await self._make_request("POST", endpoint, json_data={
            "comment": body,
        })
    
    async def get_inbox_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the inbox status.
        
        Returns:
            Dictionary with unread count, total count, and recent messages
        """
        # Get unread count
        unread_endpoint = f"/users/{self.mailbox}/mailFolders/inbox"
        folder_info = await self._make_request("GET", unread_endpoint)
        
        # Get recent messages
        recent = await self.list_messages(limit=5, unread_only=False)
        
        return {
            "mailbox": self.mailbox,
            "unread_count": folder_info.get("unreadItemCount", 0),
            "total_count": folder_info.get("totalItemCount", 0),
            "recent_messages": [
                {
                    "id": m["id"],
                    "subject": m.get("subject", "(no subject)"),
                    "from": m.get("from", {}).get("emailAddress", {}).get("address", "unknown"),
                    "received": m.get("receivedDateTime"),
                    "is_read": m.get("isRead", False),
                    "preview": m.get("bodyPreview", "")[:100],
                }
                for m in recent
            ],
        }


class GraphAPIError(Exception):
    """Exception raised for Microsoft Graph API errors."""
    
    def __init__(self, status_code: int, message: str, code: str):
        self.status_code = status_code
        self.message = message
        self.code = code
        super().__init__(f"Graph API Error ({status_code}): {code} - {message}")


# Singleton instance for reuse
_client: Optional[GraphEmailClient] = None


def get_graph_email_client() -> GraphEmailClient:
    """Get or create the Graph email client singleton."""
    global _client
    if _client is None:
        _client = GraphEmailClient()
    return _client


async def reset_client():
    """Reset the client singleton (for testing or credential rotation)."""
    global _client
    _client = None
