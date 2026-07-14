-- ============================================================
-- ADS 层：门户内容月度类型聚合统计表
-- 来源  : dwd_portal_contents
-- 聚合  : GROUP BY publish_month, content_type, category
-- 指标  : article_total, source_count
-- 行数  : 231 (742 条明细按月份+类型+分类聚合)
-- 下游  : Flask /api/analysis/content_trend
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

CREATE TABLE IF NOT EXISTS ads_portal_contents (
    publish_month STRING COMMENT '发布月份 (yyyy-MM)',
    content_type  STRING COMMENT '内容类型 (news/policy/knowledge)',
    category      STRING COMMENT '内容分类',
    article_total BIGINT COMMENT '月度文章总量',
    source_count  BIGINT COMMENT '去重发布机构数'
)
COMMENT 'ADS层 — 门户内容月度发布趋势'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE ads_portal_contents
SELECT
    DATE_FORMAT(publish_date, 'yyyy-MM') AS publish_month,
    content_type,
    category,
    COUNT(*)                      AS article_total,
    COUNT(DISTINCT source)        AS source_count
FROM dwd_portal_contents
GROUP BY DATE_FORMAT(publish_date, 'yyyy-MM'), content_type, category
ORDER BY publish_month, content_type, category;

-- 核验: ADS 行数 ＜ DWD 行数
SELECT COUNT(*) AS ads_row_count FROM ads_portal_contents;
SELECT * FROM ads_portal_contents LIMIT 10;
