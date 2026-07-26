"""SerpApi backends (https://serpapi.com/): two distinct engines under one
SERPAPI_KEY, useful for different things.

- `iter_results` (engine=bing): paginates Bing itself through SerpApi's
  hosted scraper. Reliable (no CAPTCHA), but subject to whatever Bing
  itself actually indexes for the query — confirmed empirically that Bing
  serves only a single result for a narrow `site:` query like
  `site:claude.ai/share` regardless of pagination offset (tested first=1,
  2, 10, 11, 21 — always the same 1 link).
- `iter_results_search_index` (engine=search_index): SerpApi's *own* crawled
  web index, separate from Bing/Google. For `site:claude.ai/share` this
  actually returned ~280 distinct links (vs Bing's 1) — use this one when
  you need real breadth on a `site:` query. Paginates via `start=0,10,20,...`
  (not `first=`) and stops when a page returns no new links.
"""

import os
import time

import requests

SERPAPI_URL = "https://serpapi.com/search.json"
RESULTS_PER_PAGE = 10


def _require_api_key(api_key):
    api_key = api_key or os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is not set (env var or --api-key).")
    return api_key


def iter_results(query, max_results=2000, api_key=None, delay=1.0, session=None):
    api_key = _require_api_key(api_key)
    session = session or requests.Session()
    seen_links = set()
    first = 1

    while len(seen_links) < max_results:
        params = {
            "engine": "bing",
            "q": query,
            "first": first,
            "api_key": api_key,
        }
        response = session.get(SERPAPI_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if "error" in payload:
            raise RuntimeError(f"SerpApi error: {payload['error']}")

        organic_results = payload.get("organic_results", [])
        new_on_page = 0
        for result in organic_results:
            link = result.get("link")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            new_on_page += 1
            yield {
                "position": result.get("position"),
                "title": result.get("title", ""),
                "link": link,
            }
            if len(seen_links) >= max_results:
                return

        if new_on_page == 0:
            return

        first += RESULTS_PER_PAGE
        time.sleep(delay)


def iter_results_search_index(query, max_results=2000, api_key=None, delay=1.0, session=None):
    api_key = _require_api_key(api_key)
    session = session or requests.Session()
    seen_links = set()
    start = 0

    while len(seen_links) < max_results:
        params = {
            "engine": "search_index",
            "q": query,
            "start": start,
            "api_key": api_key,
        }
        response = session.get(SERPAPI_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if "error" in payload:
            raise RuntimeError(f"SerpApi error: {payload['error']}")

        organic_results = payload.get("organic_results", [])
        new_on_page = 0
        for result in organic_results:
            link = result.get("link")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            new_on_page += 1
            yield {
                "position": result.get("position"),
                "title": result.get("title", ""),
                "link": link,
            }
            if len(seen_links) >= max_results:
                return

        if new_on_page == 0 or not payload.get("serpapi_pagination", {}).get("next"):
            return

        start += RESULTS_PER_PAGE
        time.sleep(delay)
