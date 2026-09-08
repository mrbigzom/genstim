import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

PHOTOROOM_ENDPOINT = "https://sdk.photoroom.com/v1/segment"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TRANSIENT_STATUS_CODES = {408, 425, 429}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heic",
}


class BackgroundRemovalProvider(Protocol):
    async def remove_background(self, image_path: Path, content_type: str) -> bytes: ...


class BackgroundRemovalProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class BackgroundRemovalTimeoutError(BackgroundRemovalProviderError):
    def __init__(self) -> None:
        super().__init__("provider_timeout")


class PhotoroomBackgroundRemovalProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client
        self.sleep = sleep

    async def remove_background(self, image_path: Path, content_type: str) -> bytes:
        if not self.api_key:
            raise BackgroundRemovalProviderError("provider_not_configured")

        image_bytes = await asyncio.to_thread(image_path.read_bytes)
        if self.client is not None:
            return await self._request_with_retries(self.client, image_bytes, content_type)

        async with httpx.AsyncClient() as client:
            return await self._request_with_retries(client, image_bytes, content_type)

    async def _request_with_retries(
        self,
        client: httpx.AsyncClient,
        image_bytes: bytes,
        content_type: str,
    ) -> bytes:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    PHOTOROOM_ENDPOINT,
                    headers={"x-api-key": self.api_key, "accept": "image/png"},
                    files={
                        "image_file": (
                            f"upload{CONTENT_TYPE_EXTENSIONS.get(content_type, '')}",
                            image_bytes,
                            content_type,
                        )
                    },
                    data={"format": "png", "channels": "rgba"},
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    await self._retry_delay(attempt, "timeout")
                    continue
                raise BackgroundRemovalTimeoutError() from exc
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    await self._retry_delay(attempt, "transport_error")
                    continue
                raise BackgroundRemovalProviderError("provider_unavailable") from exc

            if response.status_code == 200:
                if not response.content.startswith(PNG_SIGNATURE):
                    raise BackgroundRemovalProviderError("provider_invalid_response")
                return response.content

            if self._is_temporary(response.status_code) and attempt < self.max_retries:
                await self._retry_delay(attempt, f"http_{response.status_code}")
                continue

            raise BackgroundRemovalProviderError(self._error_code(response.status_code))

        raise BackgroundRemovalProviderError("provider_unavailable")  # pragma: no cover

    async def _retry_delay(self, attempt: int, reason: str) -> None:
        logger.warning(
            "Temporary background removal provider failure; retrying attempt=%d reason=%s",
            attempt + 1,
            reason,
        )
        await self.sleep(0.5 * (2**attempt))

    @staticmethod
    def _is_temporary(status_code: int) -> bool:
        return status_code in TRANSIENT_STATUS_CODES or status_code >= 500

    @staticmethod
    def _error_code(status_code: int) -> str:
        if status_code in {401, 403}:
            return "provider_auth_error"
        if status_code == 429:
            return "provider_rate_limited"
        if status_code in {400, 413, 415, 422}:
            return "provider_rejected_image"
        if status_code >= 500:
            return "provider_unavailable"
        return "provider_error"
