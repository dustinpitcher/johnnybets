"""
X/Twitter Media Upload Client

Handles uploading images and videos to X for attachment to tweets.
Uses X API v1.1 media upload endpoints (chunked upload for videos).

X Media Upload Flow:
1. For images (<5MB): Simple upload via POST media/upload
2. For videos/larger files: Chunked upload (INIT -> APPEND -> FINALIZE -> STATUS)

Environment variables (same as x_posting.py):
- X_API_KEY: API Key (Consumer Key)
- X_API_SECRET: API Secret (Consumer Secret)
- X_ACCESS_TOKEN: Access Token
- X_ACCESS_SECRET: Access Token Secret

Uses requests_oauthlib for OAuth 1.0a signature generation (more reliable than manual implementation).
"""
import os
import base64
import time
import asyncio
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import httpx
from requests_oauthlib import OAuth1Session


class XMediaUploadError(Exception):
    """Exception raised for X Media Upload errors."""
    
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"X Media Upload error ({status_code}): {message}")


class XMediaUploadClient:
    """
    X/Twitter API v1.1 client for uploading media.
    
    Supports:
    - Image upload (JPEG, PNG, GIF, WebP) - up to 5MB
    - Video upload (MP4) - up to 512MB via chunked upload
    - Animated GIF - up to 15MB
    """
    
    UPLOAD_BASE = "https://upload.twitter.com/1.1"
    
    # Media categories
    CATEGORY_IMAGE = "tweet_image"
    CATEGORY_GIF = "tweet_gif"
    CATEGORY_VIDEO = "tweet_video"
    
    # Chunk size for video upload (5MB)
    CHUNK_SIZE = 5 * 1024 * 1024
    
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
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            raise ValueError(
                "X API credentials required. Set X_API_KEY, X_API_SECRET, "
                "X_ACCESS_TOKEN, and X_ACCESS_SECRET environment variables."
            )
        
        # Use requests_oauthlib for proper OAuth 1.0a signature handling
        self._oauth = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_secret
        )
    
    def _detect_media_type(self, file_path: str) -> Tuple[str, str]:
        """
        Detect media type and category from file extension.
        
        Returns:
            Tuple of (mime_type, media_category)
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg", self.CATEGORY_IMAGE
        elif ext == ".png":
            return "image/png", self.CATEGORY_IMAGE
        elif ext == ".gif":
            return "image/gif", self.CATEGORY_GIF
        elif ext == ".webp":
            return "image/webp", self.CATEGORY_IMAGE
        elif ext == ".mp4":
            return "video/mp4", self.CATEGORY_VIDEO
        else:
            raise ValueError(f"Unsupported media type: {ext}")
    
    async def upload_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
    ) -> str:
        """
        Upload an image (simple upload for files under 5MB).
        
        Args:
            image_data: Raw image bytes
            media_type: MIME type of the image
            
        Returns:
            media_id string for use in tweet
        """
        url = f"{self.UPLOAD_BASE}/media/upload.json"
        
        # Base64 encode the image
        b64_data = base64.b64encode(image_data).decode("utf-8")
        
        # Use requests_oauthlib for proper OAuth signature
        # Run in executor since requests_oauthlib is synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._oauth.post(url, data={"media_data": b64_data}, timeout=60)
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"error": response.text}
            raise XMediaUploadError(
                status_code=response.status_code,
                message=str(error_data),
                details=error_data,
            )
        
        data = response.json()
        media_id = data.get("media_id_string")
        if not media_id:
            raise XMediaUploadError(500, "No media_id returned from upload")
        
        print(f"[XMediaUpload] Image uploaded: {media_id}")
        return media_id
    
    async def upload_video(
        self,
        video_data: bytes,
        media_type: str = "video/mp4",
    ) -> str:
        """
        Upload a video using chunked upload.
        
        Args:
            video_data: Raw video bytes
            media_type: MIME type of the video
            
        Returns:
            media_id string for use in tweet
        """
        total_bytes = len(video_data)
        
        # Step 1: INIT
        media_id = await self._chunked_init(total_bytes, media_type, self.CATEGORY_VIDEO)
        
        # Step 2: APPEND chunks
        segment_index = 0
        for i in range(0, total_bytes, self.CHUNK_SIZE):
            chunk = video_data[i:i + self.CHUNK_SIZE]
            await self._chunked_append(media_id, segment_index, chunk)
            segment_index += 1
        
        # Step 3: FINALIZE
        await self._chunked_finalize(media_id)
        
        # Step 4: Check processing status (for videos)
        await self._wait_for_processing(media_id)
        
        print(f"[XMediaUpload] Video uploaded: {media_id}")
        return media_id
    
    async def _chunked_init(
        self,
        total_bytes: int,
        media_type: str,
        media_category: str,
    ) -> str:
        """Initialize chunked upload."""
        url = f"{self.UPLOAD_BASE}/media/upload.json"
        
        params = {
            "command": "INIT",
            "total_bytes": str(total_bytes),
            "media_type": media_type,
            "media_category": media_category,
        }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._oauth.post(url, data=params, timeout=30)
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"error": response.text}
            raise XMediaUploadError(
                status_code=response.status_code,
                message=f"INIT failed: {error_data}",
                details=error_data,
            )
        
        data = response.json()
        media_id = data.get("media_id_string")
        if not media_id:
            raise XMediaUploadError(500, "No media_id returned from INIT")
        
        print(f"[XMediaUpload] Chunked upload initialized: {media_id}")
        return media_id
    
    async def _chunked_append(
        self,
        media_id: str,
        segment_index: int,
        chunk: bytes,
    ) -> None:
        """Append a chunk to the upload."""
        url = f"{self.UPLOAD_BASE}/media/upload.json"
        
        # For APPEND, we need to use multipart form data
        params = {
            "command": "APPEND",
            "media_id": media_id,
            "segment_index": str(segment_index),
        }
        
        # Build multipart form data
        files = {
            "media": ("chunk", chunk, "application/octet-stream"),
        }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._oauth.post(url, data=params, files=files, timeout=60)
        )
        
        # APPEND returns 204 No Content on success
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"error": response.text}
            raise XMediaUploadError(
                status_code=response.status_code,
                message=f"APPEND failed: {error_data}",
                details=error_data,
            )
        
        print(f"[XMediaUpload] Chunk {segment_index} uploaded")
    
    async def _chunked_finalize(self, media_id: str) -> Dict[str, Any]:
        """Finalize the chunked upload."""
        url = f"{self.UPLOAD_BASE}/media/upload.json"
        
        params = {
            "command": "FINALIZE",
            "media_id": media_id,
        }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._oauth.post(url, data=params, timeout=30)
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"error": response.text}
            raise XMediaUploadError(
                status_code=response.status_code,
                message=f"FINALIZE failed: {error_data}",
                details=error_data,
            )
        
        data = response.json()
        print(f"[XMediaUpload] Upload finalized: {media_id}")
        return data
    
    async def _wait_for_processing(
        self,
        media_id: str,
        max_wait: float = 120.0,
    ) -> None:
        """Wait for video processing to complete."""
        url = f"{self.UPLOAD_BASE}/media/upload.json"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            params = {
                "command": "STATUS",
                "media_id": media_id,
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._oauth.get(url, params=params, timeout=30)
            )
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"error": response.text}
                raise XMediaUploadError(
                    status_code=response.status_code,
                    message=f"STATUS check failed: {error_data}",
                    details=error_data,
                )
            
            data = response.json()
            processing_info = data.get("processing_info", {})
            state = processing_info.get("state")
            
            if state == "succeeded":
                print(f"[XMediaUpload] Processing complete: {media_id}")
                return
            elif state == "failed":
                error = processing_info.get("error", {})
                raise XMediaUploadError(
                    500,
                    f"Processing failed: {error.get('message', 'Unknown error')}",
                    error,
                )
            
            # Still processing, wait before checking again
            check_after = processing_info.get("check_after_secs", 5)
            await asyncio.sleep(check_after)
        
        raise XMediaUploadError(408, f"Processing timed out after {max_wait}s")
    
    async def upload_from_file(self, file_path: str) -> str:
        """
        Upload media from a local file path.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            media_id string for use in tweet
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")
        
        media_type, category = self._detect_media_type(file_path)
        data = path.read_bytes()
        
        if category == self.CATEGORY_VIDEO:
            return await self.upload_video(data, media_type)
        else:
            return await self.upload_image(data, media_type)
    
    async def upload_from_url(self, url: str) -> str:
        """
        Download media from a URL and upload to X.
        
        Args:
            url: URL to download the media from
            
        Returns:
            media_id string for use in tweet
        """
        # Determine media type from URL
        if url.endswith(".mp4") or "video" in url.lower():
            media_type = "video/mp4"
            is_video = True
        elif url.endswith(".gif"):
            media_type = "image/gif"
            is_video = False
        elif url.endswith(".png"):
            media_type = "image/png"
            is_video = False
        else:
            media_type = "image/jpeg"
            is_video = False
        
        # Download the media
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            data = response.content
        
        if is_video:
            return await self.upload_video(data, media_type)
        else:
            return await self.upload_image(data, media_type)


# Singleton instance
_client: Optional[XMediaUploadClient] = None


def get_x_media_upload_client() -> XMediaUploadClient:
    """Get the singleton XMediaUploadClient instance."""
    global _client
    if _client is None:
        _client = XMediaUploadClient()
    return _client
