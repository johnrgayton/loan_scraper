# loan_scraper

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

## Browser and driver compatibility

Chrome and ChromeDriver must use the same major version. For example, Chrome
147 needs ChromeDriver 147. If they drift apart, Selenium fails before any page
loads.

This project handles that in two places:

- At runtime, the scraper checks the installed Chrome and ChromeDriver versions
  when they are discoverable. If they are incompatible, it raises a clear error
  before starting the scrape.
- In Docker, the image installs a pinned Chrome for Testing build and the
  matching pinned ChromeDriver build.

The current Docker pin is:

```
CHROME_VERSION=147.0.7727.138
CHROME_VERSION_MAIN=147
```

For local non-Docker runs, set `CHROME_VERSION_MAIN` to your installed Chrome
major version so undetected-chromedriver can request a compatible driver:

```
export CHROME_VERSION_MAIN=147
```

If you want to intentionally update Chrome later, update both
`CHROME_VERSION` and `CHROME_VERSION_MAIN` in `docker-compose.yml`, then rebuild
the image. Keeping updates at build time makes scrape runs reproducible and
avoids mutating the browser installation while the scraper is running.

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

Install pinned Python dependencies for local runs:

```
python3 -m pip install -r requirements.txt
```

Set your Postgres env vars:

```
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=postgres
export PGUSER=postgres
export CHROME_VERSION_MAIN=147
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

## Running with Docker

Docker Compose starts Postgres and can run the scraper with a pinned
Chrome/ChromeDriver pair.

Start Postgres:

```
docker compose up -d postgres
```

The container exposes Postgres on host port `5433` to avoid conflicting with a
local Postgres already using `5432`. Inside Docker Compose, the scraper still
connects to `postgres:5432`.

Run the scraper:

```
docker compose run --rm scraper --market venice-fl
```

Run with filters:

```
docker compose run --rm scraper \
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

Rebuild after changing the pinned Chrome version:

```
docker compose build --pull scraper
```

The Postgres container creates the `home_loans` schema and
`home_loans.f_scraped_data` table from `docker/postgres/init.sql` when the
database volume is first initialized.

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
