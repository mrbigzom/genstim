import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import SplitResult, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_source import LeadSource
from app.repositories.lead_source import LeadSourceRepository

MAX_SOURCE_URL_LENGTH = 2048
AddressResolver = Callable[[str, int], Awaitable[set[str]]]


class LeadSourceError(Exception):
    pass


class InvalidLeadSourceURLError(LeadSourceError):
    pass


class DuplicateLeadSourceError(LeadSourceError):
    pass


async def resolve_addresses(hostname: str, port: int) -> set[str]:
    try:
        records = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise InvalidLeadSourceURLError("Source hostname could not be resolved") from exc
    return {str(record[4][0]) for record in records}


class LeadSourceService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        resolver: AddressResolver = resolve_addresses,
    ) -> None:
        self.repository = LeadSourceRepository(session)
        self.resolver = resolver

    async def add(self, raw_url: str) -> tuple[LeadSource, bool]:
        normalized, hostname, port, literal_ip = self._normalize(raw_url)
        addresses = {literal_ip} if literal_ip is not None else await self.resolver(hostname, port)
        if not addresses or any(not self._is_public_ip(address) for address in addresses):
            raise InvalidLeadSourceURLError("Source must resolve only to public IP addresses")

        existing = await self.repository.get_by_url_for_update(normalized)
        if existing is not None:
            if existing.enabled:
                raise DuplicateLeadSourceError(normalized)
            existing.enabled = True
            await self.repository.session.flush()
            return existing, False

        source = LeadSource(url=normalized, enabled=True)
        return await self.repository.create(source), True

    async def list_all(self) -> list[LeadSource]:
        return await self.repository.list_all()

    async def list_enabled(self) -> list[LeadSource]:
        return await self.repository.list_enabled()

    async def mark_scanned(self, source: LeadSource) -> None:
        source.last_scanned_at = datetime.now(UTC)
        await self.repository.session.flush()

    async def remove(self, source_id: int) -> LeadSource | None:
        if source_id <= 0:
            return None
        source = await self.repository.get_by_id_for_update(source_id)
        if source is None or not source.enabled:
            return None
        source.enabled = False
        await self.repository.session.flush()
        return source

    @staticmethod
    def _normalize(raw_url: str) -> tuple[str, str, int, str | None]:
        value = raw_url.strip()
        if (
            not value
            or len(value) > MAX_SOURCE_URL_LENGTH
            or any(character.isspace() or ord(character) < 32 for character in value)
        ):
            raise InvalidLeadSourceURLError("Source URL is empty or too long")

        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise InvalidLeadSourceURLError("Source URL is malformed") from exc
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or parsed.hostname is None:
            raise InvalidLeadSourceURLError("Only HTTP and HTTPS source URLs are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise InvalidLeadSourceURLError("Credentials are not allowed in source URLs")

        try:
            hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise InvalidLeadSourceURLError("Source hostname is invalid") from exc
        if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
            raise InvalidLeadSourceURLError("Local source URLs are not allowed")

        port = (443 if scheme == "https" else 80) if port is None else port
        if port <= 0:
            raise InvalidLeadSourceURLError("Source URL port is invalid")
        literal_ip: str | None = None
        try:
            literal_ip = str(ipaddress.ip_address(hostname))
        except ValueError:
            pass
        if literal_ip is not None and not LeadSourceService._is_public_ip(literal_ip):
            raise InvalidLeadSourceURLError("Private source IP addresses are not allowed")

        display_host = f"[{hostname}]" if ":" in hostname else hostname
        default_port = 443 if scheme == "https" else 80
        netloc = display_host if port == default_port else f"{display_host}:{port}"
        normalized = urlunsplit(
            SplitResult(scheme, netloc, parsed.path or "/", parsed.query, "")
        )
        return normalized, hostname, port, literal_ip

    @staticmethod
    def _is_public_ip(address: str) -> bool:
        try:
            return ipaddress.ip_address(address).is_global
        except ValueError:
            return False
