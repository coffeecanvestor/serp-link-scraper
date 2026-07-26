#!/usr/bin/env python3
"""CLI for paginating SerpApi search results and collecting links to CSV."""

import argparse
import csv
import sys

try:
    import truststore

    truststore.inject_into_ssl()  # trust the OS cert store (fixes corporate TLS-inspecting proxies)
except ImportError:
    pass

from dotenv import load_dotenv

from scraper import serpapi_backend


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Search query, e.g. site:example.com")
    parser.add_argument("--max-results", type=int, default=2000)
    parser.add_argument(
        "--engine",
        choices=["bing", "search_index"],
        default="search_index",
        help="SerpApi engine to use (see README for the difference)",
    )
    parser.add_argument("--output", default="links.csv")
    parser.add_argument("--api-key", help="override SERPAPI_KEY env var")
    return parser.parse_args()


def build_result_iter(args):
    if args.engine == "bing":
        return serpapi_backend.iter_results(
            args.query, max_results=args.max_results, api_key=args.api_key
        )
    if args.engine == "search_index":
        return serpapi_backend.iter_results_search_index(
            args.query, max_results=args.max_results, api_key=args.api_key
        )
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
