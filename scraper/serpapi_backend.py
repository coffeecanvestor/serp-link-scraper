"""SerpApi backend (https://serpapi.com/bing-search-api): paginates Bing
results through SerpApi's hosted scraper, which handles Bing's anti-bot
measures server-side. Requires SERPAPI_KEY (has a free tier of ~100
searches/month, then pay-as-you-go)."""

import os
import time

import requests

SERPAPI_URL = "https://serpapi.com/search.json"
RESULTS_PER_PAGE = 10


def iter_results(query, max_results=2000, api_key=None, delay=1.0, session=None):
    api_key = api_key or os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is not set (env var or --api-key).")

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
