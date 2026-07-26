# serp-link-scraper

Paginate SerpApi search results and collect all result links to CSV, up to
a configurable max (default 2000).

Two engines are available, both through the same `SERPAPI_KEY`:

| Engine         | What it queries                          | Best for                                                        |
|----------------|-------------------------------------------|------------------------------------------------------------------|
| `search_index`  | SerpApi's own crawled web index           | **Default.** Narrow `site:` queries — see caveat below on why    |
| `bing`          | Bing itself, via SerpApi's hosted scraper | General queries where you specifically want Bing's own SERP      |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and set SERPAPI_KEY (get one at https://serpapi.com/manage-api-key)
```

## Usage

```bash
python main.py --query "site:example.com" --max-results 2000
python main.py --query "site:example.com" --max-results 2000 --engine bing
python main.py --query "some regular search terms" --output results.csv
```

Results are written incrementally to `links.csv` (`--output` to change the
path), so if a run stops partway through you still keep everything
collected up to that point.

## Why two engines / caveat on `site:` queries

Search engines' own "About X results" counts are frequently a rough
estimate, not the number of results actually servable — this is
especially pronounced for narrow `site:`-restricted queries. In testing,
a `site:`-restricted query on Bing (via the `bing` engine) reported an
estimated ~580 results but only ever served **1** real result, confirmed
across five different pagination offsets. SerpApi's `search_index` engine
queries its own separately-crawled web index rather than Bing, and
returned **280** real links for the identical query — hence it's the
default here. If you need Bing's results specifically (its ranking,
snippets, etc.), use `--engine bing`, but be aware Bing itself may cap
`site:` query depth well short of its own stated estimate; the script
stops automatically once a page returns zero new links, so check the
printed "Wrote N links" count rather than assuming you'll always hit
`--max-results`.

## Notes

- Get a `SERPAPI_KEY` at [serpapi.com](https://serpapi.com/manage-api-key) (free tier available, then pay-as-you-go).
- `truststore` is included and auto-enabled to fix `SSLCertVerificationError` on networks with a TLS-inspecting corporate proxy (it falls back to the OS certificate store instead of Python's bundled one).
