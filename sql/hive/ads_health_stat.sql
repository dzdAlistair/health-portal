-- ============================================================
-- ADS 层：国民健康指标年度大类聚合统计表
-- 来源  : dwd_health_stat
-- 聚合  : GROUP BY year, category
-- 指标  : total_indicator_val (求和), avg_indicator_val (均值)
-- 行数  : 40 (因 1793 条明细聚合后大幅压缩)
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ads_health_stat;
CREATE TABLE ads_health_stat (
    year               INT    COMMENT '统计年份',
    category           STRING COMMENT '指标大类',
    total_indicator_val DOUBLE COMMENT '指标数值总和',
    avg_indicator_val  DOUBLE COMMENT '指标数值均值'
)
COMMENT 'ADS层 — 国民健康指标年度大类汇总'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE ads_health_stat
SELECT
    year,
    category,
    SUM(indicator_value)   AS total_indicator_val,
    AVG(indicator_value)   AS avg_indicator_val
FROM dwd_health_stat
GROUP BY year, category
ORDER BY year, category;

-- 核验: ADS 行数 ＜ DWD 行数
SELECT COUNT(*) AS ads_row_count FROM ads_health_stat;
SELECT * FROM ads_health_stat LIMIT 10;
