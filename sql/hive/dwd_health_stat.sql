-- ============================================================
-- DWD 层：国民健康指标清洗明细表
-- 来源  : ods_health_statistics
-- 清洗规则:
--   1. 过滤 year/category/indicator_name/indicator_value 为 NULL
--   2. 限定 year BETWEEN 1990 AND 2025
--   3. indicator_value CAST 为 DOUBLE
--   4. 按 year + category + indicator_name 联合去重
-- 行数  : ≤ 1793
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS dwd_health_stat;
CREATE TABLE dwd_health_stat (
    year            INT     COMMENT '统计年份',
    category        STRING  COMMENT '指标大类',
    indicator_name  STRING  COMMENT '指标名称',
    indicator_value DOUBLE  COMMENT '指标数值',
    unit            STRING  COMMENT '单位',
    source_url      STRING  COMMENT '数据来源URL',
    retrieved_date  STRING  COMMENT '采集日期'
)
COMMENT 'DWD层 — 国民健康指标清洗明细'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE dwd_health_stat
SELECT DISTINCT
    CAST(year AS INT) AS year,
    category,
    indicator_name,
    CAST(indicator_value AS DOUBLE) AS indicator_value,
    unit,
    source_url,
    retrieved_date
FROM ods_health_statistics
WHERE year IS NOT NULL
  AND category IS NOT NULL
  AND indicator_name IS NOT NULL
  AND indicator_value IS NOT NULL
  AND CAST(year AS INT) BETWEEN 1990 AND 2025
  AND CAST(indicator_value AS DOUBLE) IS NOT NULL;

SELECT COUNT(*) AS dwd_row_count FROM dwd_health_stat;
SELECT * FROM dwd_health_stat LIMIT 5;
