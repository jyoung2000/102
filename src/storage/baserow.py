import httpx
from src.utils.logging import logger


class BaserowClient:
    """Baserow API client for uploading wallpapers and managing rows."""

    def __init__(self, api_url: str, api_token: str, table_id: int = 810):
        self.api_url = api_url.rstrip("/")
        self.token = api_token
        self.table_id = table_id
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Token {api_token}"},
            timeout=60.0,
            follow_redirects=True,
        )

    async def upload_file(self, jpeg_bytes: bytes, filename: str) -> dict:
        """Upload a JPEG file to Baserow file storage."""
        response = await self.client.post(
            f"{self.api_url}/api/user-files/upload-file/",
            files={"file": (filename, jpeg_bytes, "image/jpeg")}
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Uploaded file to Baserow: {result.get('name', 'unknown')}")
        return result

    async def create_row(self, row_data: dict) -> dict:
        """Create a new row in the Baserow table."""
        response = await self.client.post(
            f"{self.api_url}/api/database/rows/table/{self.table_id}/?user_field_names=true",
            json=row_data
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Created Baserow row ID: {result.get('id', 'unknown')}")
        return result

    async def check_hash_exists(self, img_hash: str) -> bool:
        """Check if an image hash already exists in Baserow."""
        response = await self.client.get(
            f"{self.api_url}/api/database/rows/table/{self.table_id}/",
            params={"user_field_names": "true", "filter__imgHash__equal": img_hash}
        )
        data = response.json()
        exists = data.get("count", 0) > 0
        if exists:
            logger.info(f"Hash {img_hash} already exists in Baserow")
        return exists

    async def test_connection(self) -> dict:
        """Test connection to Baserow and return status."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/database/rows/table/{self.table_id}/",
                params={"user_field_names": "true", "page": 1, "size": 1}
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "row_count": data.get("count", 0),
                "message": f"Connected. Table has {data.get('count', 0)} rows."
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_row_count(self) -> int:
        """Get the total number of rows in the table."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/database/rows/table/{self.table_id}/",
                params={"user_field_names": "true", "page": 1, "size": 1}
            )
            data = response.json()
            return data.get("count", 0)
        except Exception:
            return 0

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
