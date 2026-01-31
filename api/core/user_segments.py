"""
User Segments Query Module for JohnnyBets Marketing

Provides database queries for user targeting:
- Get user groups with member counts
- Get users by group membership
- Get all users with verified emails

Uses asyncpg for direct PostgreSQL access since the Prisma client
is in TypeScript (Next.js) and not available in Python.

Environment variables:
- DATABASE_URL: PostgreSQL connection string
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import asyncpg


class UserSegmentsClient:
    """
    Database client for querying user segments.
    
    Connects to PostgreSQL directly using asyncpg for
    efficient async queries without the Prisma ORM.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable required for user segment queries."
            )
        
        self._pool: Optional[asyncpg.Pool] = None
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            # Parse the DATABASE_URL for asyncpg
            parsed = urlparse(self.database_url)
            
            # Handle sslmode parameter
            ssl = "require" if "sslmode=require" in self.database_url else None
            
            self._pool = await asyncpg.create_pool(
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/").split("?")[0],
                host=parsed.hostname,
                port=parsed.port or 5432,
                ssl=ssl,
                min_size=1,
                max_size=5,
            )
        
        return self._pool
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def get_user_groups(self) -> List[Dict[str, Any]]:
        """
        Get all user groups with member counts.
        
        Returns:
            List of groups with id, name, description, and member_count
        """
        pool = await self._get_pool()
        
        query = """
            SELECT 
                ug.id,
                ug.name,
                ug.description,
                COUNT(ugm.id) as member_count
            FROM user_groups ug
            LEFT JOIN user_group_memberships ugm ON ugm.group_id = ug.id
            GROUP BY ug.id, ug.name, ug.description
            ORDER BY ug.name
        """
        
        rows = await pool.fetch(query)
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "member_count": row["member_count"],
            }
            for row in rows
        ]
    
    async def get_users_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        """
        Get all users in a specific group.
        
        Args:
            group_name: Name of the group (e.g., "beta_testers")
            
        Returns:
            List of users with id, name, email
        """
        pool = await self._get_pool()
        
        query = """
            SELECT 
                u.id,
                u.name,
                u.email,
                u.tier,
                u.last_active_at
            FROM users u
            INNER JOIN user_group_memberships ugm ON ugm.user_id = u.id
            INNER JOIN user_groups ug ON ug.id = ugm.group_id
            WHERE ug.name = $1
            AND u.email IS NOT NULL
            ORDER BY u.name
        """
        
        rows = await pool.fetch(query, group_name)
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "tier": row["tier"],
                "last_active": row["last_active_at"].isoformat() if row["last_active_at"] else None,
            }
            for row in rows
        ]
    
    async def get_all_users_with_email(
        self,
        verified_only: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all users with email addresses.
        
        Args:
            verified_only: If True, only return users with verified emails
            limit: Optional limit on number of users
            
        Returns:
            List of users with id, name, email, tier
        """
        pool = await self._get_pool()
        
        query = """
            SELECT 
                id,
                name,
                email,
                tier,
                message_count,
                last_active_at,
                created_at
            FROM users
            WHERE email IS NOT NULL
        """
        
        if verified_only:
            query += " AND email_verified IS NOT NULL"
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = await pool.fetch(query)
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "tier": row["tier"],
                "message_count": row["message_count"],
                "last_active": row["last_active_at"].isoformat() if row["last_active_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    
    async def get_users_by_tier(self, tier: str) -> List[Dict[str, Any]]:
        """
        Get all users by subscription tier.
        
        Args:
            tier: User tier (free, pro, enterprise)
            
        Returns:
            List of users with id, name, email
        """
        pool = await self._get_pool()
        
        query = """
            SELECT 
                id,
                name,
                email,
                tier,
                last_active_at
            FROM users
            WHERE tier = $1
            AND email IS NOT NULL
            ORDER BY name
        """
        
        rows = await pool.fetch(query, tier)
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "tier": row["tier"],
                "last_active": row["last_active_at"].isoformat() if row["last_active_at"] else None,
            }
            for row in rows
        ]
    
    async def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get users who have been active in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of active users with id, name, email
        """
        pool = await self._get_pool()
        
        query = """
            SELECT 
                id,
                name,
                email,
                tier,
                message_count,
                last_active_at
            FROM users
            WHERE email IS NOT NULL
            AND last_active_at > NOW() - INTERVAL '%s days'
            ORDER BY last_active_at DESC
        """ % days  # Using % formatting since asyncpg doesn't support interval placeholders well
        
        rows = await pool.fetch(query)
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "tier": row["tier"],
                "message_count": row["message_count"],
                "last_active": row["last_active_at"].isoformat() if row["last_active_at"] else None,
            }
            for row in rows
        ]
    
    async def get_segment_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all available segments for targeting.
        
        Returns:
            Dictionary with group counts, tier breakdown, and totals
        """
        pool = await self._get_pool()
        
        # Get total users with email
        total_query = """
            SELECT COUNT(*) as total FROM users WHERE email IS NOT NULL
        """
        total_row = await pool.fetchrow(total_query)
        
        # Get tier breakdown
        tier_query = """
            SELECT tier, COUNT(*) as count 
            FROM users 
            WHERE email IS NOT NULL 
            GROUP BY tier
        """
        tier_rows = await pool.fetch(tier_query)
        
        # Get group summary
        groups = await self.get_user_groups()
        
        # Get active users count (last 7 days)
        active_query = """
            SELECT COUNT(*) as count 
            FROM users 
            WHERE email IS NOT NULL 
            AND last_active_at > NOW() - INTERVAL '7 days'
        """
        active_row = await pool.fetchrow(active_query)
        
        return {
            "total_users_with_email": total_row["total"],
            "active_last_7_days": active_row["count"],
            "by_tier": {row["tier"]: row["count"] for row in tier_rows},
            "groups": groups,
        }


# Singleton instance for reuse
_client: Optional[UserSegmentsClient] = None


def get_user_segments_client() -> UserSegmentsClient:
    """Get or create the user segments client singleton."""
    global _client
    if _client is None:
        _client = UserSegmentsClient()
    return _client


async def reset_client():
    """Reset the client singleton (for testing or reconnection)."""
    global _client
    if _client:
        await _client.close()
    _client = None
