-- Migration: Add category column to products table
-- This migration adds support for product categorization

-- Add category column to products table
ALTER TABLE products
ADD COLUMN category VARCHAR(100) NULL
AFTER store;

-- Add index for category filtering
CREATE INDEX idx_category ON products(category);

-- Update the product_summary view to include category
CREATE OR REPLACE VIEW product_summary AS
SELECT
    p.id,
    p.asin,
    p.title,
    p.store,
    p.category,
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
