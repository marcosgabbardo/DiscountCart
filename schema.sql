-- Amazon Price Monitor Database Schema
-- Execute this script to create the database and tables

CREATE DATABASE IF NOT EXISTS amazon_price_monitor
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE amazon_price_monitor;

-- Table: products
-- Stores the monitored products and their target prices
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(20) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(500),
    image_url VARCHAR(500),
    target_price DECIMAL(10, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    lowest_price DECIMAL(10, 2),
    highest_price DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_asin (asin),
    INDEX idx_is_active (is_active)
);

-- Table: price_history
-- Stores historical price data for each product
CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    was_available BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_recorded (product_id, recorded_at)
);

-- Table: alerts
-- Stores alert configurations and their status
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    alert_type ENUM('target_reached', 'price_drop', 'below_average') NOT NULL,
    threshold_value DECIMAL(10, 2),
    threshold_percentage DECIMAL(5, 2),
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_price DECIMAL(10, 2),
    triggered_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_alert (product_id, is_active),
    INDEX idx_triggered (is_triggered)
);

-- Table: notifications
-- Stores notification history
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NOT NULL,
    product_id INT NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('console', 'email', 'telegram') DEFAULT 'console',
    was_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_alert_notification (alert_id)
);

-- View: product_summary
-- Provides a quick summary of products with their alert status
CREATE OR REPLACE VIEW product_summary AS
SELECT
    p.id,
    p.asin,
    p.title,
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
