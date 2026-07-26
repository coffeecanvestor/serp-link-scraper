"""Free Bing SERP scraper: paginates https://www.bing.com/search and
extracts organic result links. No API key required, but best-effort only
(see README for ToS/robots.txt caveats and blocking behavior).

Uses curl_cffi (impersonating a real Chrome TLS fingerprint) instead of
plain `requests`. Plain `requests` gets soft-blocked by Bing even with a
correct User-Agent header: Bing fingerprints the TLS handshake itself
(JA3-style), and Python's default TLS stack doesn't look like a real
browser no matter what headers you set. Confirmed empirically on this repo
(see README) — with plain `requests`, Bing returns HTTP 200 but silently
omits the results container from the HTML.

Also confirmed empirically: Bing applies extra scrutiny to `site:` operator
queries specifically — even with the TLS fix and a primed session/cookies,
`site:` queries frequently come back with zero results for a scripted
client while an identical non-`site:` query returns results normally. If
`--engine free` reports 0 links for a `site:` query, that's very likely
this, not a bug — fall back to `--engine serpapi` or `--engine dataforseo`,
both of which handle `site:` queries fine since they submit the query
through their own managed browser/proxy infrastructure.
"""

import base64
import random
import sys
import time
from urllib.parse import parse_qs, urlparse

from curl_cffi import requests
from bs4 import BeautifulSoup

BING_SEARCH_URL = "https://www.bing.com/search"

CHROME_IMPERSONATIONS = ["chrome124", "chrome120", "chrome123"]

RESULTS_PER_PAGE = 10


class BlockedError(RuntimeError):
    """Raised when Bing appears to have blocked/CAPTCHA'd the request."""


def _new_session():
    session = requests.Session(impersonate=random.choice(CHROME_IMPERSONATIONS))
    session.headers.update({"Accept-Language": "en-US,en;q=0.9"})
    session.get(BING_SEARCH_URL.rsplit("/", 1)[0] + "/", timeout=15)  # prime cookies
    return session


def _looks_blocked(response):
    if response.status_code in (403, 429):
        return True
    text_lower = response.text.lower()
    return "g-recaptcha" in text_lower or "/challenge" in response.url.lower()


def _resolve_link(href):
    """Bing wraps most organic result hrefs in a bing.com/ck/a tracking
    redirect with the real destination base64-encoded in the `u` query
    param (prefixed with a 2-char encoding-version tag, e.g. "a1"). Decode
    it so the CSV has usable destination URLs, not bing.com redirects."""
    parsed = urlparse(href)
    if parsed.netloc and "bing.com" in parsed.netloc and parsed.path == "/ck/a":
        u = parse_qs(parsed.query).get("u", [None])[0]
        if u:
            encoded = u[2:] if len(u) > 2 and u[1].isdigit() else u
            padded = encoded + "=" * (-len(encoded) % 4)
            try:
                return base64.urlsafe_b64decode(padded).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                pass
    return href


def _parse_results(html):
    soup = BeautifulSoup(html, "lxml")
    results = []
    for position, li in enumerate(soup.select("li.b_algo"), start=1):
        anchor = li.select_one("h2 a")
        if anchor is None or not anchor.get("href"):
            continue
        results.append(
            {
                "position": position,
                "title": anchor.get_text(strip=True),
                "link": _resolve_link(anchor["href"]),
            }
        )
    return results


def iter_results(query, max_results=2000, delay_min=3.0, delay_max=6.0, session=None):
    """Yield unique {position, title, link} dicts for `query`, paginating
    Bing until `max_results` is reached, the index is exhausted, or a
    block is detected (raises BlockedError, caller decides whether to stop
    or fall back to a paid backend)."""
    session = session or _new_session()
    seen_links = set()
    first = 1

    while len(seen_links) < max_results:
        params = {"q": query, "first": first}
        response = session.get(BING_SEARCH_URL, params=params, timeout=15)

        if _looks_blocked(response):
            raise BlockedError(
                f"Bing appears to have blocked this request at first={first} "
                f"(status={response.status_code}). Collected {len(seen_links)} links "
                "so far. Consider the serpapi/dataforseo backend instead."
            )

        page_results = _parse_results(response.text)
        new_on_page = 0
        for result in page_results:
            if result["link"] in seen_links:
                continue
            seen_links.add(result["link"])
            new_on_page += 1
            yield result
            if len(seen_links) >= max_results:
                return

        if new_on_page == 0:
            if first == 1 and ":" in query:
                print(
                    "Warning: 0 results on the first page for an operator query "
                    "(e.g. site:/intitle:/etc). Bing frequently suppresses operator "
                    "queries for scripted clients even when regular queries work "
                    "fine — try --engine serpapi or --engine dataforseo instead.",
                    file=sys.stderr,
                )
            return  # reached the end of Bing's index for this query

        first += RESULTS_PER_PAGE
        time.sleep(random.uniform(delay_min, delay_max))
