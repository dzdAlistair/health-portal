-- ============================================================
-- DWD 层：健康产业产品备案清洗明细表
-- 来源  : ods_health_industry
-- 清洗规则:
--   1. 全核心字段非空过滤
--   2. industry_type 枚举校验 (医疗器械/药品制造/药品研发)
--   3. approval_date 日期格式校验
--   4. 按 industry_id + product_name + approval_date 联合去重
-- 行数  : ≤ 500
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

CREATE TABLE IF NOT EXISTS dwd_health_industry (
    industry_id      STRING  COMMENT '备案ID',
    industry_type    STRING  COMMENT '产业类型',
    product_name     STRING  COMMENT '产品名称',
    category         STRING  COMMENT '产品品类',
    registrant_region STRING COMMENT '注册地区',
    approval_date    DATE    COMMENT '获批日期',
    status           STRING  COMMENT '状态',
    source           STRING  COMMENT '数据来源',
    source_url       STRING  COMMENT '来源URL'
)
COMMENT 'DWD层 — 健康产业产品备案清洗明细'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE dwd_health_industry
SELECT DISTINCT
    industry_id,
    industry_type,
    product_name,
    category,
    registrant_region,
    try_cast(approval_date AS DATE) AS approval_date,
    status,
    source,
    source_url
FROM ods_health_industry
WHERE industry_id IS NOT NULL
  AND industry_type IS NOT NULL
  AND product_name IS NOT NULL
  AND category IS NOT NULL
  AND approval_date IS NOT NULL
  AND status IS NOT NULL
  AND industry_type IN ('医疗器械', '药品制造', '药品研发')
  AND try_cast(approval_date AS DATE) IS NOT NULL;

SELECT COUNT(*) AS dwd_row_count FROM dwd_health_industry;
SELECT * FROM dwd_health_industry LIMIT 5;
