-- ============================================================
-- ODS 层：健康产业产品备案原始数据（外部表）
-- 数据源：health_industry.csv
-- HDFS : /health_portal/raw/industry/
-- 行数 : 500
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

CREATE EXTERNAL TABLE IF NOT EXISTS ods_health_industry (
    industry_id      STRING  COMMENT '备案ID',
    industry_type    STRING  COMMENT '产业类型 (医疗器械/药品制造/药品研发)',
    product_name     STRING  COMMENT '产品名称',
    category         STRING  COMMENT '产品品类',
    registrant_region STRING COMMENT '注册地区',
    approval_date    STRING  COMMENT '获批日期',
    status           STRING  COMMENT '状态',
    source           STRING  COMMENT '数据来源',
    source_url       STRING  COMMENT '来源URL'
)
COMMENT 'ODS层 — 健康产业产品备案原始数据'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/health_portal/raw/industry/'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT COUNT(*) AS row_count FROM ods_health_industry;
SELECT * FROM ods_health_industry LIMIT 5;
