CREATE SCHEMA IF NOT EXISTS home_loans;

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
