import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExternalAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ExternalAPIService:
    def __init__(self, auth_token: Optional[str] = None):
        self.base_url = settings.base_api_url
        self.auth_token = auth_token

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def get_attendance(self, event_id: int) -> dict:
        url = f"{self.base_url}/attendance/{event_id}"
        params = {"type": "detailed"}

        logger.info(f"Fetching attendance from {url}")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=self._get_headers())

                if response.status_code == 404:
                    raise ExternalAPIError(
                        f"Event {event_id} not found in external API",
                        status_code=404,
                        details={"event_id": event_id}
                    )

                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"External API returned status {response.status_code}",
                        status_code=response.status_code,
                        details={"response": response.text[:500]}
                    )

                data = response.json()
                logger.info(f"Attendance data received: {data.get('attendance_count', 0)} attendees")
                return data

        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"Failed to connect to external API: {e}",
                details={"url": url, "error": str(e)}
            )


external_api_service = ExternalAPIService()
