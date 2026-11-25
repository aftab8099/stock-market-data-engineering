-- Report §4.9, Listings 4.7–4.10 and §5.5, Listing 5.1.
-- Run against PostgreSQL (stock_market_db) or SQLite — all four
-- queries use standard SQL / window functions both support.
-- Replace 'AAPL' with a symbol present in your loaded dataset.

-- 5.1 / Listing 5.1 — records stored per symbol
SELECT symbol, COUNT(*) AS total_records,
       MIN(trade_date) AS first_trading_date,
       MAX(trade_date) AS latest_trading_date
FROM stock_prices
GROUP BY symbol
ORDER BY symbol;

-- Listing 4.7 — retrieve historical prices
SELECT symbol, trade_date, open_price, high_price, low_price, close_price, volume
FROM stock_prices
WHERE symbol = 'AAPL'
ORDER BY trade_date;

-- Listing 4.8 — daily price change (LAG window function)
SELECT symbol, trade_date, close_price,
       close_price - LAG(close_price) OVER (
           PARTITION BY symbol ORDER BY trade_date
       ) AS daily_price_change
FROM stock_prices
ORDER BY symbol, trade_date;

-- Listing 4.9 — daily percentage return
WITH price_changes AS (
    SELECT symbol, trade_date, close_price,
           LAG(close_price) OVER (
               PARTITION BY symbol ORDER BY trade_date
           ) AS previous_close
    FROM stock_prices
)
SELECT symbol, trade_date, close_price, previous_close,
       ROUND(((close_price - previous_close) / NULLIF(previous_close, 0)) * 100, 4)
           AS daily_return_pct
FROM price_changes
ORDER BY symbol, trade_date;

-- Listing 4.10 — five-observation moving average
SELECT symbol, trade_date, close_price,
       AVG(close_price) OVER (
           PARTITION BY symbol ORDER BY trade_date
           ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
       ) AS moving_average_5
FROM stock_prices
ORDER BY symbol, trade_date;
