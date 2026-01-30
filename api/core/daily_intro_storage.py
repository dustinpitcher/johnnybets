"""
Daily Intro Storage

Handles storage and retrieval of daily intro messages from Azure Blob Storage.
Falls back to local file storage if Azure is not configured.
"""
import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
from zoneinfo import ZoneInfo


class DailyIntroStorage:
    """
    Stores and retrieves daily intro messages from Azure Blob Storage.
    
    Storage structure:
    - daily-intros/{date}/intro.json
    
    JSON structure:
    {
        "content": "markdown string",
        "generated_at": "ISO timestamp",
        "games_featured": ["PHI @ NYK", "LAL @ GSW", ...],
        "sports": ["nba", "nhl"],
        "expires_at": "ISO timestamp (next day 8 AM ET)"
    }
    """
    
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("DAILY_INTRO_CONTAINER_NAME", "daily-intros")
        self.local_storage_dir = Path(os.getenv("LOCAL_DAILY_INTRO_DIR", "./data/daily-intros"))
        
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
                # Ensure container exists
                try:
                    self._container_client.create_container()
                except Exception:
                    pass  # Container already exists
            except ImportError:
                print("[DailyIntroStorage] azure-storage-blob not installed, using local files")
                self._blob_service_client = False
            except Exception as e:
                print(f"[DailyIntroStorage] Failed to connect to Azure Blob Storage: {e}")
                self._blob_service_client = False
        return self._container_client
    
    def _get_date_str(self, date: Optional[datetime] = None) -> str:
        """Get date string in ET timezone for storage path."""
        eastern = ZoneInfo("America/New_York")
        if date is None:
            date = datetime.now(eastern)
        elif date.tzinfo is None:
            date = date.replace(tzinfo=eastern)
        else:
            date = date.astimezone(eastern)
        return date.strftime("%Y-%m-%d")
    
    def _get_blob_path(self, date_str: str) -> str:
        """Generate blob path for a given date."""
        return f"{date_str}/intro.json"
    
    async def save(
        self,
        content: str,
        games_featured: List[str],
        sports: List[str],
    ) -> bool:
        """
        Save a daily intro to storage.
        
        Args:
            content: The markdown intro content
            games_featured: List of games mentioned (e.g., ["PHI @ NYK", "LAL @ GSW"])
            sports: List of sports covered (e.g., ["nba", "nhl"])
            
        Returns:
            True if saved successfully, False otherwise
        """
        eastern = ZoneInfo("America/New_York")
        now_et = datetime.now(eastern)
        date_str = self._get_date_str(now_et)
        
        # Calculate expiration (8 AM ET next day)
        expires_at = now_et.replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        if now_et.hour >= 8:
            # After 8 AM, expires at 8 AM next day
            from datetime import timedelta
            expires_at = expires_at + timedelta(days=1)
        
        data = {
            "content": content,
            "generated_at": now_et.isoformat(),
            "games_featured": games_featured,
            "sports": sports,
            "expires_at": expires_at.isoformat(),
            "date": date_str,
        }
        
        container_client = self._get_blob_client()
        
        if container_client:
            # Save to Azure Blob Storage
            try:
                blob_path = self._get_blob_path(date_str)
                blob_client = container_client.get_blob_client(blob_path)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: blob_client.upload_blob(
                        json.dumps(data, indent=2),
                        overwrite=True
                    )
                )
                
                print(f"[DailyIntroStorage] Saved intro to blob: {blob_path}")
                return True
                
            except Exception as e:
                print(f"[DailyIntroStorage] Failed to save to blob: {e}")
                # Fall through to local save
        
        # Fall back to local storage
        try:
            self.local_storage_dir.mkdir(parents=True, exist_ok=True)
            local_path = self.local_storage_dir / f"{date_str}.json"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: local_path.write_text(json.dumps(data, indent=2))
            )
            
            print(f"[DailyIntroStorage] Saved intro to local file: {local_path}")
            return True
            
        except Exception as e:
            print(f"[DailyIntroStorage] Failed to save locally: {e}")
            return False
    
    async def get(self, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Get the daily intro for a given date.
        
        Args:
            date: The date to fetch (defaults to today in ET)
            
        Returns:
            The intro data dict or None if not found
        """
        date_str = self._get_date_str(date)
        
        container_client = self._get_blob_client()
        
        if container_client:
            # Try Azure Blob Storage first
            try:
                blob_path = self._get_blob_path(date_str)
                blob_client = container_client.get_blob_client(blob_path)
                
                loop = asyncio.get_event_loop()
                blob_data = await loop.run_in_executor(
                    None,
                    lambda: blob_client.download_blob().readall()
                )
                
                data = json.loads(blob_data)
                print(f"[DailyIntroStorage] Loaded intro from blob: {blob_path}")
                return data
                
            except Exception as e:
                print(f"[DailyIntroStorage] Failed to load from blob: {e}")
                # Fall through to local
        
        # Try local storage
        try:
            local_path = self.local_storage_dir / f"{date_str}.json"
            if local_path.exists():
                loop = asyncio.get_event_loop()
                data_str = await loop.run_in_executor(
                    None,
                    lambda: local_path.read_text()
                )
                data = json.loads(data_str)
                print(f"[DailyIntroStorage] Loaded intro from local file: {local_path}")
                return data
        except Exception as e:
            print(f"[DailyIntroStorage] Failed to load locally: {e}")
        
        return None
    
    async def get_current(self) -> Optional[Dict[str, Any]]:
        """
        Get the current valid daily intro.
        
        Returns the intro for today if it exists and hasn't expired.
        """
        data = await self.get()
        
        if data is None:
            return None
        
        # Check if expired
        try:
            eastern = ZoneInfo("America/New_York")
            expires_at = datetime.fromisoformat(data["expires_at"])
            now_et = datetime.now(eastern)
            
            if now_et > expires_at:
                print("[DailyIntroStorage] Intro has expired")
                return None
        except Exception:
            pass  # If we can't parse expiration, return the data anyway
        
        return data


# Singleton instance
_storage: Optional[DailyIntroStorage] = None


def get_storage() -> DailyIntroStorage:
    """Get the singleton DailyIntroStorage instance."""
    global _storage
    if _storage is None:
        _storage = DailyIntroStorage()
    return _storage
