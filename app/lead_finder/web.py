import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import aiohttp

from app.lead_finder.extractors import extract_public_page
from app.lead_finder.types import LeadCandidate

USER_AGENT = "GenStimLeadFinder/1.0 (+manual-review-only)"
MAX_PAGE_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 256_000
MAX_REDIRECTS = 3


class PublicWebsiteError(Exception):
    pass


class UnsafePublicUrlError(PublicWebsiteError):
    pass


class RobotsDeniedError(PublicWebsiteError):
    pass


class PublicWebsiteScanner:
    async def scan(self, *, url: str, niche: str) -> LeadCandidate:
        normalized_url = await validate_public_url(url)
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        ) as session:
            await self._check_robots(session, normalized_url)
            final_url, html = await self._fetch_html(session, normalized_url)
        return extract_public_page(html=html, url=final_url, niche=niche)

    async def _check_robots(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> None:
        parsed = urlsplit(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            status, body, _ = await self._fetch(
                session,
                robots_url,
                max_bytes=MAX_ROBOTS_BYTES,
                accept_html=False,
            )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise PublicWebsiteError("Could not verify robots.txt") from exc
        if status in {401, 403} or status >= 500:
            raise RobotsDeniedError("Website does not currently permit automated access")
        if status == 200:
            robots = RobotFileParser()
            robots.set_url(robots_url)
            robots.parse(body.splitlines())
            if not robots.can_fetch(USER_AGENT, url):
                raise RobotsDeniedError("robots.txt disallows this URL")

    async def _fetch_html(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> tuple[str, str]:
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            status, body, headers = await self._fetch(
                session,
                current_url,
                max_bytes=MAX_PAGE_BYTES,
                accept_html=True,
            )
            if status in {301, 302, 303, 307, 308}:
                location = headers.get("Location")
                if not location:
                    raise PublicWebsiteError("Website returned an invalid redirect")
                current_url = await validate_public_url(urljoin(current_url, location))
                continue
            if status != 200:
                raise PublicWebsiteError(f"Website returned HTTP {status}")
            return current_url, body
        raise PublicWebsiteError("Website redirected too many times")

    async def _fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        max_bytes: int,
        accept_html: bool,
    ) -> tuple[int, str, aiohttp.typedefs.LooseHeaders]:
        try:
            async with session.get(url, allow_redirects=False) as response:
                content_type = response.headers.get("Content-Type", "").casefold()
                if accept_html and response.status == 200 and "text/html" not in content_type:
                    raise PublicWebsiteError("URL does not return an HTML page")
                chunks = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        raise PublicWebsiteError("Public page exceeds the safe size limit")
                encoding = response.charset or "utf-8"
                return response.status, chunks.decode(encoding, errors="replace"), response.headers
        except TimeoutError as exc:
            raise PublicWebsiteError("Website request timed out") from exc
        except aiohttp.ClientError as exc:
            raise PublicWebsiteError("Website request failed") from exc


async def validate_public_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise UnsafePublicUrlError("Only public HTTP(S) URLs are supported")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafePublicUrlError("URL port is invalid") from exc
    if port not in {80, 443}:
        raise UnsafePublicUrlError("Only standard HTTP(S) ports are supported")

    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafePublicUrlError("Public hostname could not be resolved") from exc
    if not addresses:
        raise UnsafePublicUrlError("Public hostname could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise UnsafePublicUrlError("Private and local network addresses are not allowed")
    return parsed.geturl()
