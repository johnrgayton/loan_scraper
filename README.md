# loan_scraper

** This project is used for personal use only and is not, nor should the data herein, be used for commercial purposes. **

This project scrapes Homes.com listing pages to capture property details and
mortgage history data, then stores the results in Postgres for analysis. The
primary goal is to support research into assumable loans by collecting a
consistent, queryable dataset from listing pages.

## What data is captured

Each listing produces a single row with these fields (aligned to the Postgres
table):

- session_id: Selenium session identifier for tracing when a run restarts.
- listing_id: Homes.com listing identifier from the URL (e.g., w3p44ve2xfvs9).
- property_url: Full listing URL.
- market: Market slug used to generate listing URLs.
- address: Street address only.
- city: City parsed from the listing address.
- state: State parsed from the listing address.
- zip: Zip code parsed from the listing address.
- current_list_price: Integer list price (currency symbols removed).
- features: JSONB array of normalized feature strings.
- beds: Beds value as scraped.
- baths: Baths value as scraped (often includes decimals like 2.5).
- square_feet: Integer square footage (commas removed).
- listing_description: Full description text.
- scraped_at: UTC timestamp for when the row was inserted.
- mortgage_history: JSONB array of mortgage rows, each with:
  - date
  - status
  - amount (integer)
  - loan_type

## How it works

The scraper uses Selenium (undetected-chromedriver) to load listing pages and
extract data from stable page elements. Mortgage history is pulled directly
from the table under the "Mortgage History" heading (no click-through).

## Waits and sleeps (anti-flake + anti-bot)

Homes.com pages load content dynamically as you scroll. The scraper uses:

- Explicit waits (WebDriverWait + expected conditions) to ensure key elements
  are present before scraping.
- Targeted jittered sleeps to allow lazy-loaded blocks to render and reduce
  automation detection.

You can tune sleep timing using environment variables:

- SCRAPER_SLEEP_MIN (default: 1.5 seconds)
- SCRAPER_SLEEP_MAX (default: 3.5 seconds)

## Postgres output

The scraper inserts directly into Postgres using psycopg2 and JSONB fields for
features and mortgage history. This makes it easy to pivot features or unpack
mortgage rows later.

Expected table structure:

```
CREATE TABLE IF NOT EXISTS home_loans.f_scraped_data (
    scraped_at TIMESTAMP DEFAULT NOW(),
    session_id VARCHAR(256),
    listing_id VARCHAR(128),
    property_url VARCHAR(1000),
    market VARCHAR(256),
    address VARCHAR(256),
    city VARCHAR(256),
    state CHAR(2),
    zip CHAR(5),
    current_list_price INTEGER,
    features JSONB,
    beds INTEGER,
    baths NUMERIC(2,1),
    square_feet INTEGER,
    listing_description TEXT,
    mortgage_history JSONB
);
```

## Running the scraper

Set your Postgres env vars:

```
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=postgres
export PGUSER=postgres
```

If you use .pgpass for the password (recommended), add:

```
localhost:5432:postgres:postgres:YOUR_PASSWORD_HERE
```

Then run:

```
PGHOST=localhost PGPORT=5432 PGDATABASE=postgres PGUSER=postgres \
PYTHONPATH=src python3 -m loan_scraper --market venice-fl
```

Full example with filters:

```
PGHOST=localhost PGPORT=5432 PGDATABASE=postgres PGUSER=postgres \
PYTHONPATH=src python3 -m loan_scraper \
  --market venice-fl \
  --bed-min 4 \
  --bed-max 5 \
  --sfmin 1500 \
  --bath-min 2 \
  --bath-max 5 \
  --parking 2 \
  --price-max 600000 \
  --exclude-active-adult true \
  --require-garage true
```

To omit any filter, set it to `any` (for example, `--sfmin any` or
`--bath-max any`). This removes it from the URL.
```

## Tests

Unit tests live in `tests/test_scraper.py`. The live scrape test is skipped by
default. Run it like this:

```
RUN_LIVE_SCRAPE=1 PGHOST=localhost PGPORT=5432 PGDATABASE=postgres PGUSER=postgres \
PYTHONPATH=src pytest -k live
```

## Notes and tips

- If the site changes selectors or headings, update the XPaths and class names
  in `src/loan_scraper/scraper.py`.
- Features are normalized to lowercase strings and stored as a JSONB array to
  allow comparisons and pivots in SQL.
- Mortgage history is stored as an array of objects so you can expand it later
  with `jsonb_array_elements`.
