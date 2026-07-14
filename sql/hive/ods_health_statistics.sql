-- ============================================================
-- ODS 层：国民健康指标原始数据（外部表）
-- 数据源：health_statistics.csv
-- HDFS : /health_portal/raw/health_statistics/
-- 行数 : 1793
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ods_health_statistics;
CREATE EXTERNAL TABLE ods_health_statistics (
    year            STRING  COMMENT '统计年份',
    category        STRING  COMMENT '指标大类 (如 一类农村/中城市)',
    indicator_name  STRING  COMMENT '指标名称',
    indicator_value STRING  COMMENT '指标数值',
    unit            STRING  COMMENT '单位',
    source_url      STRING  COMMENT '数据来源URL',
    retrieved_date  STRING  COMMENT '采集日期'
)
COMMENT 'ODS层 — 国民健康指标原始数据'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/health_portal/raw/health_statistics/'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT COUNT(*) AS row_count FROM ods_health_statistics;
SELECT * FROM ods_health_statistics LIMIT 5;
