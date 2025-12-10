-- Migration: Add store column to products table
-- Run this if you already have an existing database
-- Compatible with MySQL 5.7+ and MariaDB 10.3+

-- Add the store column (will fail if already exists - that's OK)
ALTER TABLE products
ADD COLUMN store ENUM('zaffari', 'carrefour') NOT NULL DEFAULT 'zaffari'
AFTER image_url;

-- Add index on store for filtering (ignore error if exists)
ALTER TABLE products ADD INDEX idx_store (store);

-- Update the view to include store
CREATE OR REPLACE VIEW product_summary AS
SELECT
    p.id,
    p.asin,
    p.title,
    p.store,
    p.current_price,
    p.target_price,
    p.lowest_price,
    p.highest_price,
    ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)), 2) AS avg_price_7days,
    ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)), 2) AS avg_price_30days,
    (SELECT COUNT(*) FROM price_history ph WHERE ph.product_id = p.id) AS total_price_records,
    CASE
        WHEN p.current_price <= p.target_price THEN 'TARGET_REACHED'
        WHEN p.current_price < p.lowest_price THEN 'NEW_LOW'
        ELSE 'MONITORING'
    END AS status,
    p.is_active,
    p.updated_at
FROM products p
WHERE p.is_active = TRUE;
