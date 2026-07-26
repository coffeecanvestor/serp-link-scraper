"""DataForSEO backend (https://docs.dataforseo.com/v3/serp/bing/organic/live/advanced/):
uses the synchronous "live/advanced" Bing organic SERP endpoint. Requires
DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD (HTTP basic auth).

Note: DataForSEO's organic "depth" parameter caps out at 700 results per
task (per their docs, subject to change) and this endpoint doesn't expose
an offset/"start" param to page past that in a single keyword task. So this
backend can reliably get you up to ~700 links; for anything beyond that,
use --engine free or --engine serpapi instead, or split your query further
(e.g. narrower `site:` + date/keyword filters).
"""

import os

import requests

DATAFORSEO_URL = "https://api.dataforseo.com/v3/serp/bing/organic/live/advanced"
MAX_DEPTH = 700


def iter_results(
    query,
    max_results=2000,
    login=None,
    password=None,
    location_code=2840,  # United States
    language_code="en",
    session=None,
):
    login = login or os.environ.get("DATAFORSEO_LOGIN")
    password = password or os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise RuntimeError("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD are not set.")

    depth = min(max_results, MAX_DEPTH)
    session = session or requests.Session()

    payload = [
        {
            "keyword": query,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
        }
    ]
    response = session.post(
        DATAFORSEO_URL,
        json=payload,
        auth=(login, password),
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()

    if body.get("status_code") != 20000:
        raise RuntimeError(f"DataForSEO error: {body.get('status_message')}")

    seen_links = set()
    for task in body.get("tasks", []):
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                if item.get("type") != "organic":
                    continue
                link = item.get("url")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                yield {
                    "position": item.get("rank_absolute"),
                    "title": item.get("title", ""),
                    "link": link,
                }
                if len(seen_links) >= max_results:
                    return
