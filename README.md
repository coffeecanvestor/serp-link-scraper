# bing-serp-scraper

Paginate Bing search results and collect result links to CSV — up to a
configurable max (default 2000), with a choice of three backends depending
on how much you want to spend:

| Engine       | Cost                          | Reliability                                      |
|--------------|--------------------------------|---------------------------------------------------|
| `free`       | $0                              | Best-effort; works well for normal queries, but Bing suppresses `site:`-operator results for scripted clients (see caveats) |
| `serpapi`    | Free tier (~100/mo), then paid  | High — SerpApi handles Bing's anti-bot measures    |
| `dataforseo` | Paid, cheap at scale            | High, but capped at ~700 results per query (depth) |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # only needed for serpapi / dataforseo engines
```

## Usage

```bash
# Free: direct Bing scraping, randomized 3-6s delay + UA rotation
python main.py --query "site:claude.ai/share" --max-results 2000 --engine free

# SerpApi (needs SERPAPI_KEY in .env or --api-key)
python main.py --query "site:claude.ai/share" --max-results 2000 --engine serpapi

# DataForSEO (needs DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in .env)
python main.py --query "site:claude.ai/share" --max-results 2000 --engine dataforseo
```

Results are written incrementally to `links.csv` (`--output` to change the
path), so if a run stops partway through (hit a CAPTCHA, ran out of results,
hit a depth cap) you still keep everything collected up to that point.

## Important caveats (found while building/testing this)

- **`free` engine and Bing's Terms of Service**: scraping Bing's HTML search
  results directly is against Bing's ToS and disallowed by its
  `robots.txt` for most bots. This is common practice for small/occasional
  jobs, but Bing *will* eventually rate-limit or CAPTCHA requests that come
  too fast or too often — there's no way around this other than slowing
  down (already built in) or switching to `serpapi`/`dataforseo`, which are
  Bing-authorized/managed access paths.
- **Plain `requests` doesn't work at all anymore, even with a correct
  User-Agent**: Bing fingerprints the TLS handshake itself. A `requests`
  call with a real Chrome User-Agent header still gets HTTP 200 back with
  the results container silently missing from the HTML — no error, no
  CAPTCHA, just empty. `free_scraper.py` uses `curl_cffi` with
  `impersonate="chrome124"` to present a genuine Chrome TLS fingerprint,
  which fixes this.
- **Bing suppresses `site:` operator queries specifically for scripted
  clients** — confirmed by testing `site:github.com`, `site:wikipedia.org`,
  and `site:claude.ai` all returning zero results even with the TLS fix and
  a cookie-primed session, while an identical query *without* the `site:`
  operator (e.g. `claude ai share`) returns normal results immediately. If
  `--engine free` prints the "0 results on the first page for an operator
  query" warning, that's this — not a bug, and not something a delay/UA
  tweak fixes. Use `--engine serpapi` or `--engine dataforseo` for `site:`
  queries; they submit the query through their own infrastructure and
  aren't subject to this.
- **Bing wraps organic result links in `bing.com/ck/a` tracking redirects**,
  not direct URLs — `free_scraper.py` decodes the base64-encoded `u=`
  param back to the real destination URL before writing it to CSV.
- **Actual result depth**: for a narrow `site:` query, Bing (and by
  extension SerpApi) often stops serving new results well before 2000, even
  if the "About X results" estimate is higher. The `free`/`serpapi` engines
  stop automatically once a page returns zero new links; check the printed
  "Wrote N links" count rather than assuming you'll always get the max.
- **`dataforseo` depth cap**: DataForSEO's Bing organic `live/advanced`
  endpoint caps at 700 results per task and has no offset param to page
  further within one keyword — use `free` or `serpapi` if you need more
  than that for a single query.
