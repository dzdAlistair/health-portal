-- ============================================================
-- ADS 层：健康产业产品品类聚合统计表
-- 来源  : dwd_health_industry
-- 聚合  : GROUP BY industry_type, category
-- 指标  : total_product_count, distinct_product_count,
--         earliest_approval_date, latest_approval_date
-- 行数  : 22 (3 产业类型 × ~7 品类)
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

CREATE TABLE IF NOT EXISTS ads_health_industry (
    industry_type          STRING COMMENT '产业类型',
    category               STRING COMMENT '产品品类',
    total_product_count    BIGINT COMMENT '产品备案总数',
    distinct_product_count BIGINT COMMENT '去重产品数',
    earliest_approval_date STRING COMMENT '最早获批日期',
    latest_approval_date   STRING COMMENT '最晚获批日期'
)
COMMENT 'ADS层 — 健康产业产品品类汇总'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE ads_health_industry
SELECT
    industry_type,
    category,
    COUNT(*)                    AS total_product_count,
    COUNT(DISTINCT product_name) AS distinct_product_count,
    MIN(approval_date)          AS earliest_approval_date,
    MAX(approval_date)          AS latest_approval_date
FROM dwd_health_industry
GROUP BY industry_type, category
ORDER BY industry_type, category;

-- 核验: ADS 行数 ＜ DWD 行数
SELECT COUNT(*) AS ads_row_count FROM ads_health_industry;
SELECT * FROM ads_health_industry LIMIT 10;
