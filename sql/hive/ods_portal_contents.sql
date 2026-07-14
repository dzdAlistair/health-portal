-- ============================================================
-- ODS 层：门户内容原始数据（外部表）
-- 数据源：portal_contents.csv
-- HDFS : /health_portal/raw/internet/
-- 行数 : 742
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ods_portal_contents;
CREATE EXTERNAL TABLE ods_portal_contents (
    content_id   STRING  COMMENT '内容唯一编号',
    content_type STRING  COMMENT '内容类型 (news/policy/knowledge)',
    title        STRING  COMMENT '文章标题',
    category     STRING  COMMENT '内容分类',
    publish_date STRING  COMMENT '发布日期',
    source       STRING  COMMENT '发布机构',
    source_url   STRING  COMMENT '原始网页地址',
    status       STRING  COMMENT '发布状态'
)
COMMENT 'ODS层 — 门户内容原始数据'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/health_portal/raw/internet/'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT COUNT(*) AS row_count FROM ods_portal_contents;
SELECT * FROM ods_portal_contents LIMIT 5;
