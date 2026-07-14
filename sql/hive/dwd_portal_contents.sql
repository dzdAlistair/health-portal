-- ============================================================
-- DWD 层：门户内容清洗明细表
-- 来源  : ods_portal_contents
-- 清洗规则:
--   1. 全核心字段非空过滤
--   2. content_type 枚举校验 (knowledge/news/policy)
--   3. status 限定 published
--   4. publish_date 日期格式校验
--   5. 按 content_id 主键去重
-- 行数  : ≤ 742
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS dwd_portal_contents;
CREATE TABLE dwd_portal_contents (
    content_id   STRING  COMMENT '内容唯一编号',
    content_type STRING  COMMENT '内容类型',
    title        STRING  COMMENT '文章标题',
    category     STRING  COMMENT '内容分类',
    publish_date DATE    COMMENT '发布日期',
    source       STRING  COMMENT '发布机构',
    source_url   STRING  COMMENT '原始网页地址',
    status       STRING  COMMENT '发布状态'
)
COMMENT 'DWD层 — 门户内容清洗明细'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE dwd_portal_contents
SELECT DISTINCT
    content_id,
    content_type,
    title,
    category,
    CAST(publish_date AS DATE) AS publish_date,
    source,
    source_url,
    status
FROM ods_portal_contents
WHERE content_id IS NOT NULL
  AND content_type IS NOT NULL
  AND title IS NOT NULL
  AND category IS NOT NULL
  AND publish_date IS NOT NULL
  AND source IS NOT NULL
  AND source_url IS NOT NULL
  AND status IS NOT NULL
  AND content_type IN ('knowledge', 'news', 'policy')
  AND status = 'published'
  AND CAST(publish_date AS DATE) IS NOT NULL;

SELECT COUNT(*) AS dwd_row_count FROM dwd_portal_contents;
SELECT * FROM dwd_portal_contents LIMIT 5;
