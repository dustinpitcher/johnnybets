"""
Media Generation Client

Handles image and video generation for JohnnyBets marketing.
- Images: Gemini 3 Pro via OpenRouter (best quality)
- Videos: xAI Grok Imagine (only option for video)

Supports storage to Azure Blob Storage or local filesystem.

Environment variables:
- OPENROUTER_API_KEY: OpenRouter API key (for Gemini 3 Pro images)
- XAI_API_KEY: xAI API key (for video generation)
- AZURE_STORAGE_CONNECTION_STRING: Azure Blob Storage connection string
- MEDIA_STORAGE_CONTAINER: Container name for media (default: "marketing-media")
"""
import os
import json
import asyncio
import httpx
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pathlib import Path
from uuid import uuid4


class XAIMediaError(Exception):
    """Exception raised for xAI Media API errors."""
    
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"xAI Media API error ({status_code}): {message}")


class MediaClient:
    """
    Client for image and video generation.
    
    - Images: Gemini 3 Pro via OpenRouter (best quality, ~25s)
    - Videos: xAI Grok Imagine (async with polling, ~30-60s)
    
    Features:
    - Automatic storage to Azure Blob or local filesystem
    - Prompt enhancement for consistent brand style
    """
    
    OPENROUTER_BASE = "https://openrouter.ai/api/v1"
    XAI_BASE = "https://api.x.ai/v1"
    IMAGE_MODEL = "google/gemini-3-pro-image-preview"
    VIDEO_MODEL = "grok-imagine-video"
    
    # Default prompt suffixes for brand consistency
    # Keep it simple - let the model be creative with the branding
    BRAND_SUFFIX = "include JohnnyBets.AI logo in sans-serif font with color: #22c55e neon green. Bet responsibly 21+."
    
    # Style presets - minimal prompting
    STYLE_PRESETS = {
        "matchup": "Meticulous designer. Take time with text layout. Bold sports matchup graphic. Black background. Diagonal team color clash. Giant condensed typography. Stats with labels.",
        "terminal": "Meticulous designer. Take time with text layout. Terminal on black. ASCII art logos from text characters. Monospace. Team colors. No window chrome.",
        "stats": "Meticulous designer. Take time with text layout. Sports stat card. Dark background. Clean data layout. Team color accents.",
        "promo": "Meticulous designer. Take time with text layout. Dynamic sports promo. Bold type with motion. Team colors collide. Stats animate in.",
        "hype": "Meticulous designer. Take time with text layout. Athletic campaign aesthetic. Diagonal color slash. Massive bold typography. Motion streaks.",
    }
    
    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        xai_api_key: Optional[str] = None,
        storage_connection_string: Optional[str] = None,
        storage_container: Optional[str] = None,
        local_storage_dir: Optional[str] = None,
    ):
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.xai_api_key = xai_api_key or os.getenv("XAI_API_KEY")
        self.storage_connection_string = storage_connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.storage_container = storage_container or os.getenv("MEDIA_STORAGE_CONTAINER", "marketing-media")
        self.local_storage_dir = Path(local_storage_dir or os.getenv("LOCAL_MEDIA_DIR", "./data/marketing-media"))
        
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable required for image generation")
        
        # Lazy-load blob client
        self._blob_service_client = None
        self._container_client = None
    
    def _get_openrouter_headers(self) -> Dict[str, str]:
        """Get request headers for OpenRouter API."""
        return {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
        }
    
    def _get_xai_headers(self) -> Dict[str, str]:
        """Get request headers for xAI API."""
        return {
            "Authorization": f"Bearer {self.xai_api_key}",
            "Content-Type": "application/json",
        }
    
    def _get_blob_client(self):
        """Get or create the Azure Blob Storage client."""
        if self._blob_service_client is None and self.storage_connection_string:
            try:
                from azure.storage.blob import BlobServiceClient
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    self.storage_connection_string
                )
                self._container_client = self._blob_service_client.get_container_client(
                    self.storage_container
                )
                # Ensure container exists
                try:
                    self._container_client.create_container()
                except Exception:
                    pass  # Container already exists
            except ImportError:
                print("[MediaClient] azure-storage-blob not installed, using local files")
                self._blob_service_client = False
            except Exception as e:
                print(f"[MediaClient] Failed to connect to Azure Blob Storage: {e}")
                self._blob_service_client = False
        return self._container_client
    
    async def _store_media(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """
        Store media content to Azure Blob or local filesystem.
        
        Returns:
            URL or local path to the stored media
        """
        container_client = self._get_blob_client()
        
        if container_client:
            # Store to Azure Blob Storage
            try:
                blob_path = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{filename}"
                blob_client = container_client.get_blob_client(blob_path)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: blob_client.upload_blob(
                        content,
                        content_type=content_type,
                        overwrite=True
                    )
                )
                
                # Return the blob URL
                url = blob_client.url
                print(f"[MediaClient] Stored media to blob: {blob_path}")
                return url
                
            except Exception as e:
                print(f"[MediaClient] Failed to store to blob: {e}, falling back to local")
        
        # Fall back to local storage
        self.local_storage_dir.mkdir(parents=True, exist_ok=True)
        date_dir = self.local_storage_dir / datetime.now(timezone.utc).strftime('%Y/%m/%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        
        local_path = date_dir / filename
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: local_path.write_bytes(content)
        )
        
        print(f"[MediaClient] Stored media locally: {local_path}")
        return str(local_path)
    
    async def _download_media(self, url: str) -> bytes:
        """Download media from a URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return response.content
    
    def _build_prompt(
        self,
        base_prompt: str,
        style: Optional[str] = None,
        include_branding: bool = True,
    ) -> str:
        """
        Build a complete prompt with style preset and branding.
        
        Args:
            base_prompt: The core content description
            style: Optional style preset key (matchup, terminal, stats, promo)
            include_branding: Whether to append JohnnyBets branding
            
        Returns:
            Complete prompt string
        """
        parts = []
        
        # Add style preset if specified
        if style and style in self.STYLE_PRESETS:
            parts.append(self.STYLE_PRESETS[style])
        
        # Add the base prompt
        parts.append(base_prompt)
        
        # Add branding
        if include_branding:
            parts.append(self.BRAND_SUFFIX)
        
        return " ".join(parts)
    
    async def generate_image(
        self,
        prompt: str,
        style: Optional[str] = None,
        aspect_ratio: str = "16:9",
        include_branding: bool = True,
        store: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate an image using Gemini 3 Pro via OpenRouter.
        
        Args:
            prompt: Description of the image to generate
            style: Optional style preset (matchup, terminal, stats, promo, hype)
            aspect_ratio: Image aspect ratio (default 16:9 for social media)
            include_branding: Whether to include JohnnyBets branding in prompt
            store: Whether to download and store the image
            
        Returns:
            Dictionary with:
            - url: Data URL of the generated image (base64)
            - revised_prompt: The full prompt used
            - stored_path: Local/blob path if stored
        """
        full_prompt = self._build_prompt(prompt, style, include_branding)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.OPENROUTER_BASE}/chat/completions",
                headers=self._get_openrouter_headers(),
                json={
                    "model": self.IMAGE_MODEL,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "modalities": ["image", "text"],
                    "image_config": {"aspect_ratio": aspect_ratio},
                },
                timeout=120.0,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise XAIMediaError(
                    status_code=response.status_code,
                    message=error_data.get("error", {}).get("message", response.text),
                    details=error_data,
                )
            
            data = response.json()
        
        # Extract image from OpenRouter response
        result = {
            "url": None,
            "revised_prompt": full_prompt,
            "stored_path": None,
        }
        
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            images = message.get("images", [])
            if images:
                img_url = images[0].get("image_url", {}).get("url", "")
                result["url"] = img_url
        
        # Store the image if requested
        if store and result["url"] and result["url"].startswith("data:image"):
            try:
                # Extract base64 data from data URL
                header, b64data = result["url"].split(",", 1)
                content = base64.b64decode(b64data)
                
                # Determine extension from header
                ext = "png" if "png" in header else "jpg"
                mime = "image/png" if ext == "png" else "image/jpeg"
                
                filename = f"image_{uuid4().hex[:8]}.{ext}"
                stored_path = await self._store_media(content, filename, mime)
                result["stored_path"] = stored_path
            except Exception as e:
                print(f"[MediaClient] Failed to store image: {e}")
        
        return result
    
    async def generate_video(
        self,
        prompt: str,
        style: Optional[str] = None,
        duration: int = 6,
        aspect_ratio: str = "16:9",
        resolution: Literal["720p", "480p"] = "720p",
        include_branding: bool = True,
        store: bool = True,
        poll_interval: float = 5.0,
        max_wait: float = 120.0,
    ) -> Dict[str, Any]:
        """
        Generate a video using xAI's Grok Imagine API.
        
        This is an async operation - the method submits the request,
        polls for completion, and returns when the video is ready.
        
        Args:
            prompt: Description of the video to generate
            style: Optional style preset (matchup, terminal, stats, promo)
            duration: Video duration in seconds (1-15, default 6)
            aspect_ratio: Video aspect ratio (default 16:9)
            resolution: Video resolution (720p or 480p)
            include_branding: Whether to include JohnnyBets branding
            store: Whether to download and store the video
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for completion
            
        Returns:
            Dictionary with:
            - url: URL to the generated video
            - duration: Actual video duration
            - stored_path: Local/blob path if stored
            - request_id: The xAI request ID
        """
        if not self.xai_api_key:
            raise XAIMediaError(400, "XAI_API_KEY required for video generation")
        
        full_prompt = self._build_prompt(prompt, style, include_branding)
        
        # Submit video generation request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.XAI_BASE}/videos/generations",
                headers=self._get_xai_headers(),
                json={
                    "model": "grok-imagine-video",
                    "prompt": full_prompt,
                    "duration": min(max(duration, 1), 15),  # Clamp to 1-15
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                },
                timeout=30.0,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise XAIMediaError(
                    status_code=response.status_code,
                    message=error_data.get("error", response.text),
                    details=error_data,
                )
            
            data = response.json()
        
        request_id = data.get("request_id")
        if not request_id:
            raise XAIMediaError(500, "No request_id returned from video generation")
        
        print(f"[MediaClient] Video generation started: {request_id}")
        
        # Poll for completion
        start_time = asyncio.get_event_loop().time()
        result = None
        
        while asyncio.get_event_loop().time() - start_time < max_wait:
            await asyncio.sleep(poll_interval)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.XAI_BASE}/videos/{request_id}",
                    headers=self._get_xai_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 404:
                    # Still processing
                    continue
                
                if response.status_code >= 400:
                    error_data = response.json() if response.text else {}
                    raise XAIMediaError(
                        status_code=response.status_code,
                        message=error_data.get("error", response.text),
                        details=error_data,
                    )
                
                data = response.json()
                video_data = data.get("video", {})
                
                if video_data.get("url"):
                    result = {
                        "url": video_data.get("url"),
                        "duration": video_data.get("duration"),
                        "request_id": request_id,
                        "stored_path": None,
                    }
                    break
        
        if not result:
            raise XAIMediaError(408, f"Video generation timed out after {max_wait}s")
        
        print(f"[MediaClient] Video generation completed: {request_id}")
        
        # Download and store if requested
        if store and result["url"]:
            try:
                content = await self._download_media(result["url"])
                filename = f"video_{uuid4().hex[:8]}.mp4"
                stored_path = await self._store_media(content, filename, "video/mp4")
                result["stored_path"] = stored_path
            except Exception as e:
                print(f"[MediaClient] Failed to store video: {e}")
        
        return result
    
    async def generate_video_from_image(
        self,
        image_url: str,
        prompt: str,
        duration: int = 6,
        aspect_ratio: str = "16:9",
        resolution: Literal["720p", "480p"] = "720p",
        store: bool = True,
        poll_interval: float = 5.0,
        max_wait: float = 120.0,
    ) -> Dict[str, Any]:
        """
        Animate an existing image into a video.
        
        Args:
            image_url: URL to the source image (must be publicly accessible)
            prompt: Description of how to animate the image
            duration: Video duration in seconds (1-15)
            aspect_ratio: Video aspect ratio
            resolution: Video resolution
            store: Whether to download and store the video
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            
        Returns:
            Same as generate_video()
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.XAI_BASE}/videos/generations",
                headers=self._get_xai_headers(),
                json={
                    "model": "grok-imagine-video",
                    "prompt": prompt,
                    "image_url": image_url,
                    "duration": min(max(duration, 1), 15),
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                },
                timeout=30.0,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise XAIMediaError(
                    status_code=response.status_code,
                    message=error_data.get("error", response.text),
                    details=error_data,
                )
            
            data = response.json()
        
        request_id = data.get("request_id")
        if not request_id:
            raise XAIMediaError(500, "No request_id returned")
        
        # Poll for completion (same as generate_video)
        start_time = asyncio.get_event_loop().time()
        result = None
        
        while asyncio.get_event_loop().time() - start_time < max_wait:
            await asyncio.sleep(poll_interval)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.XAI_BASE}/videos/{request_id}",
                    headers=self._get_xai_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 404:
                    continue
                
                if response.status_code >= 400:
                    error_data = response.json() if response.text else {}
                    raise XAIMediaError(
                        status_code=response.status_code,
                        message=error_data.get("error", response.text),
                        details=error_data,
                    )
                
                data = response.json()
                video_data = data.get("video", {})
                
                if video_data.get("url"):
                    result = {
                        "url": video_data.get("url"),
                        "duration": video_data.get("duration"),
                        "request_id": request_id,
                        "stored_path": None,
                    }
                    break
        
        if not result:
            raise XAIMediaError(408, f"Video generation timed out after {max_wait}s")
        
        if store and result["url"]:
            try:
                content = await self._download_media(result["url"])
                filename = f"video_{uuid4().hex[:8]}.mp4"
                stored_path = await self._store_media(content, filename, "video/mp4")
                result["stored_path"] = stored_path
            except Exception as e:
                print(f"[MediaClient] Failed to store video: {e}")
        
        return result


# Singleton instance
_client: Optional[MediaClient] = None


def get_media_client() -> MediaClient:
    """Get the singleton MediaClient instance."""
    global _client
    if _client is None:
        _client = MediaClient()
    return _client


# Backwards compatibility alias
def get_xai_media_client() -> MediaClient:
    """Deprecated: Use get_media_client() instead."""
    return get_media_client()
