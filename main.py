#!/usr/bin/env python3
"""CLI for scraping Bing SERP links, paginated, via a choice of backends."""

import argparse
import csv
import sys

try:
    import truststore

    truststore.inject_into_ssl()  # trust the OS cert store (fixes corporate TLS-inspecting proxies)
except ImportError:
    pass

from dotenv import load_dotenv

from scraper import dataforseo_backend, free_scraper, serpapi_backend


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="site:claude.ai/share", help="Search query")
    parser.add_argument("--max-results", type=int, default=2000)
    parser.add_argument(
        "--engine",
        choices=["free", "serpapi", "serpapi_index", "dataforseo"],
        default="free",
    )
    parser.add_argument("--output", default="links.csv")
    parser.add_argument("--delay-min", type=float, default=3.0, help="free engine only")
    parser.add_argument("--delay-max", type=float, default=6.0, help="free engine only")
    parser.add_argument("--api-key", help="override SERPAPI_KEY env var")
    return parser.parse_args()


def build_result_iter(args):
    if args.engine == "free":
        return free_scraper.iter_results(
            args.query,
            max_results=args.max_results,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
        )
    if args.engine == "serpapi":
        return serpapi_backend.iter_results(
            args.query, max_results=args.max_results, api_key=args.api_key
        )
    if args.engine == "serpapi_index":
        return serpapi_backend.iter_results_search_index(
            args.query, max_results=args.max_results, api_key=args.api_key
        )
    if args.engine == "dataforseo":
        return dataforseo_backend.iter_results(args.query, max_results=args.max_results)
    raise ValueError(f"Unknown engine: {args.engine}")


def main():
    load_dotenv()
    args = parse_args()
    result_iter = build_result_iter(args)

    count = 0
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["position", "title", "link"])
        writer.writeheader()
        try:
            for result in result_iter:
                writer.writerow(result)
                f.flush()
                count += 1
                if count % 50 == 0:
                    print(f"...{count} links collected", file=sys.stderr)
        except Exception as exc:
            print(f"Stopped early after {count} links: {exc}", file=sys.stderr)
            print(f"Wrote {count} links to {args.output}")
            sys.exit(1)

    print(f"Wrote {count} links to {args.output}")


if __name__ == "__main__":
    main()
