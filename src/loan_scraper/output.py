import os

import psycopg2
from psycopg2.extras import Json, execute_values


def _null_if_empty(value):
    if value in ("", None):
        return None
    return value


def _normalize_features(features):
    if not features:
        return []
    if isinstance(features, str):
        features = [features]
    normalized = []
    seen = set()
    for feat in features:
        if not isinstance(feat, str):
            continue
        cleaned = " ".join(feat.split()).strip().lower()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def _get_db_config():
    return {
        "host": os.getenv("PGHOST"),
        "port": os.getenv("PGPORT", "5432"),
        "dbname": os.getenv("PGDATABASE"),
        "user": os.getenv("PGUSER"),
        "password": os.getenv("PGPASSWORD"),
        "sslmode": os.getenv("PGSSLMODE", "prefer"),
    }


def write_listing_data(final_data):
    if not final_data:
        return

    db_config = _get_db_config()
    missing = [key for key in ("host", "dbname", "user") if not db_config.get(key)]
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"Missing required Postgres settings: {missing_list}")

    conn = psycopg2.connect(**db_config)
    try:
        rows = []
        for dat in final_data:
            if len(dat) < 11:
                continue
            (
                property_url,
                address,
                price,
                features,
                beds,
                baths,
                square_feet,
                description,
                session_id,
                mortgage_history,
                listing_id,
            ) = dat
            features_json = _normalize_features(features)
            rows.append(
                (
                    session_id,
                    property_url,
                    address,
                    price,
                    Json(features_json),
                    _null_if_empty(beds),
                    _null_if_empty(baths),
                    _null_if_empty(square_feet),
                    description,
                    Json(mortgage_history),
                    listing_id,
                )
            )

        with conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO home_loans.f_scraped_data (
                        session_id,
                        property_url,
                        address,
                        current_list_price,
                        features,
                        beds,
                        baths,
                        square_feet,
                        listing_description,
                        mortgage_history,
                        listing_id
                    )
                    VALUES %s
                    """,
                    rows,
                )
    finally:
        conn.close()
