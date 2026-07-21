"""Company research utility.

Given a prospect's website URL, crawl a handful of key pages on that site
(top page + about/business/news-style pages found via internal links) and
supplement that with Claude's server-side web search for industry context,
recent news, and competitive landscape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import anthropic
import requests
from bs4 import BeautifulSoup

_USER_AGENT = (
    "Mozilla/5.0 (compatible; ProposalResearchBot/1.0; "
    "+for-management-consulting-proposal-drafting)"
)
_REQUEST_TIMEOUT = 10
_MAX_PAGES = 5
_MAX_CHARS_PER_PAGE = 6000

# Keywords (Japanese + English) used to identify high-value internal pages
# such as "company overview", "business", "news/IR", "recruiting".
_LINK_KEYWORDS = [
    "会社概要", "企業情報", "会社案内", "企業理念", "about",
    "事業内容", "事業紹介", "サービス", "products", "business", "service",
    "ニュース", "プレスリリース", "news", "press",
    "ir", "投資家", "採用", "recruit", "careers",
]


class CompanyResearchError(Exception):
    """Raised when the prospect's website cannot be reached or parsed."""


@dataclass
class CompanyResearch:
    company_name: str
    site_text: str
    web_search_summary: str
    sources: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def research_company_from_url(
    url: str,
    api_key: str,
    company_name: str = "",
) -> CompanyResearch:
    """Research a prospect company starting from their website URL.

    Fetches the top page plus a handful of linked "about/business/news"
    pages on the same domain, then runs a supplementary Claude web search
    for industry trends / recent news. Raises ``CompanyResearchError`` if
    the top page itself cannot be reached.
    """
    normalized_url = _normalize_url(url)

    try:
        home_html, home_title = _fetch_page(normalized_url)
    except Exception as exc:  # noqa: BLE001
        raise CompanyResearchError(
            f"指定されたURLにアクセスできませんでした（{normalized_url}）: {exc}"
        ) from exc

    pages: list[tuple[str, str, str]] = [
        (normalized_url, home_title, _extract_visible_text(home_html))
    ]
    sources = [normalized_url]

    for link_url, label in _find_candidate_links(home_html, normalized_url):
        if len(pages) >= _MAX_PAGES:
            break
        try:
            html, title = _fetch_page(link_url)
        except Exception:  # noqa: BLE001
            continue  # skip unreachable sub-pages, don't abort the whole research
        pages.append((link_url, title or label, _extract_visible_text(html)))
        sources.append(link_url)

    site_text_parts: list[str] = []
    for page_url, title, text in pages:
        stripped = text.strip()
        if not stripped:
            continue
        snippet = stripped[:_MAX_CHARS_PER_PAGE]
        site_text_parts.append(f"=== {title or page_url} ({page_url}) ===\n{snippet}")
    site_text = "\n\n".join(site_text_parts)

    resolved_name = company_name.strip() or _guess_company_name(home_title, normalized_url)

    web_search_summary = _search_supplementary_info(resolved_name, normalized_url, api_key)

    return CompanyResearch(
        company_name=resolved_name,
        site_text=site_text,
        web_search_summary=web_search_summary,
        sources=sources,
    )


# ---------------------------------------------------------------------------
# Page fetching / parsing
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise CompanyResearchError("URLが入力されていません。")
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def _fetch_page(url: str) -> tuple[str, str]:
    """Return (html, title) for *url*. Raises on network/HTTP errors."""
    resp = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT},
        timeout=_REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    return html, title


def _extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _find_candidate_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return (url, anchor_text) pairs for same-domain links that look like
    company-overview / business / news pages, ranked by keyword relevance."""
    soup = BeautifulSoup(html, "html.parser")
    base_netloc = urlparse(base_url).netloc

    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != base_netloc:
            continue  # stay on the prospect's own domain

        clean_url = parsed._replace(fragment="").geturl()
        if clean_url in seen or clean_url == base_url:
            continue

        anchor_text = a.get_text(strip=True)
        haystack = f"{anchor_text} {href}".lower()
        if any(keyword.lower() in haystack for keyword in _LINK_KEYWORDS):
            seen.add(clean_url)
            candidates.append((clean_url, anchor_text))

    return candidates


def _guess_company_name(home_title: str, url: str) -> str:
    if home_title:
        # Titles are often "会社名｜キャッチコピー" or "会社名 - Home" — take the first segment.
        for sep in ["｜", "|", "-", "–", "：", ":"]:
            if sep in home_title:
                candidate = home_title.split(sep)[0].strip()
                if candidate:
                    return candidate
        return home_title.strip()
    return urlparse(url).netloc


# ---------------------------------------------------------------------------
# Supplementary Claude web search (industry trends / news / competitors)
# ---------------------------------------------------------------------------

def _search_supplementary_info(company_name: str, url: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""「{company_name}」（Webサイト: {url}）について、生成AI活用の提案書作成に必要な補足情報を収集してください。

以下の観点から情報を検索・整理してください：
1. 業界内でのポジション・競合他社との違い
2. 直近のニュース・プレスリリース・IR情報（あれば）
3. 経営課題・事業課題として報じられている、または推測される内容
4. 既存のDX・AI活用に関する取り組みや方針（あれば）
5. 業界全体における生成AI活用のトレンド

収集した情報を日本語で詳細にまとめてください。情報が見つからない場合は、業界一般的な動向を補足してください。"""

    messages = [{"role": "user", "content": prompt}]

    # Server-side web search: Claude handles the search loop internally.
    # We may receive pause_turn if the server loop hits its iteration cap;
    # in that case we re-send to let Claude continue.
    MAX_CONTINUATIONS = 5
    response = None
    for _ in range(MAX_CONTINUATIONS):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4000,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue

        break

    if response is None:
        return ""

    text_parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts).strip()
