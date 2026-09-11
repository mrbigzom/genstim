import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.lead_finder.catalog import NICHES, infer_niche
from app.lead_finder.scoring import score_public_lead
from app.lead_finder.types import LeadCandidate

EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PUBLIC_CONTACT_HOSTS = {"t.me", "telegram.me", "instagram.com", "www.instagram.com"}


class PublicPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_title = ""
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._in_title = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and values.get("property") == "og:title":
            self.meta_title = values.get("content", "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if self._in_title:
            self.title = f"{self.title} {cleaned}".strip()


def extract_public_page(
    *,
    html: str,
    url: str,
    niche: str,
    source: str = "website",
) -> LeadCandidate:
    if niche not in NICHES:
        raise ValueError(f"Unsupported lead niche: {niche}")
    parser = PublicPageParser()
    parser.feed(html)
    visible_text = " ".join(parser.text_parts)
    name = (parser.meta_title or parser.title or urlsplit(url).hostname or "Public page").strip()
    contact = _extract_public_contact(parser.links, visible_text, url)
    score, reason_fit = score_public_lead(
        text=visible_text,
        niche=niche,
        contact=contact,
        source=source,
    )
    return LeadCandidate(
        name=name[:255],
        source=source,
        url=url[:2048],
        niche=niche,
        contact=contact[:255],
        reason_fit=reason_fit[:1000],
        score=score,
    )


def extract_public_telegram_channel(
    *,
    title: str,
    username: str,
    text: str,
) -> LeadCandidate | None:
    niche = infer_niche(f"{title} {text}")
    if niche is None:
        return None
    contact = f"@{username}"
    score, reason_fit = score_public_lead(
        text=f"{title} {text}",
        niche=niche,
        contact=contact,
        source="telegram_channel",
    )
    return LeadCandidate(
        name=title[:255],
        source="telegram_channel",
        url=f"https://t.me/{username}"[:2048],
        niche=niche,
        contact=contact[:255],
        reason_fit=reason_fit[:1000],
        score=score,
    )


def _extract_public_contact(links: list[str], text: str, base_url: str) -> str:
    for href in links:
        if href.casefold().startswith("mailto:"):
            return href.split(":", maxsplit=1)[1].split("?", maxsplit=1)[0].strip()
    email = EMAIL_PATTERN.search(text)
    if email:
        return email.group(0)
    for href in links:
        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
        if parsed.hostname and parsed.hostname.casefold() in PUBLIC_CONTACT_HOSTS:
            return absolute
    return ""
