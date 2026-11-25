-- Report §3.6, Listing 3.1 and §4.5, Listing 4.4.
-- Run against PostgreSQL after creating the database:
--   CREATE DATABASE stock_market_db;
--   psql -d stock_market_db -f sql/schema.sql
CREATE DATABASE stock_market_db;

-- Connect to stock_market_db, then:
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol      VARCHAR(20)    NOT NULL,
    trade_date  DATE           NOT NULL,
    open_price  NUMERIC(14, 4),
    high_price  NUMERIC(14, 4),
    low_price   NUMERIC(14, 4),
    close_price NUMERIC(14, 4),
    volume      BIGINT,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, trade_date),
    CHECK (high_price IS NULL OR low_price IS NULL OR high_price >= low_price),
    CHECK (volume IS NULL OR volume >= 0)
);

-- UPSERT (Report §4.7, Listing 4.6): insert a new observation, or
-- update it when the (symbol, trade_date) already exists.
-- INSERT INTO stock_prices
--     (symbol, trade_date, open_price, high_price, low_price, close_price, volume)
-- VALUES (%s, %s, %s, %s, %s, %s, %s)
-- ON CONFLICT (symbol, trade_date) DO UPDATE SET
--     open_price  = EXCLUDED.open_price,
--     high_price  = EXCLUDED.high_price,
--     low_price   = EXCLUDED.low_price,
--     close_price = EXCLUDED.close_price,
--     volume      = EXCLUDED.volume;
