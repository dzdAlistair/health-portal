-- ============================================================
-- ADS 层：医疗资源省份年度聚合统计表
-- 来源  : dwd_medical_resource
-- 聚合  : GROUP BY province, year
-- 指标  : total_institutions, total_beds, total_doctors, total_nurses
-- 行数  : 310 (31 省 × 10 年)
-- 下游  : Flask /api/analysis/institution_by_region
--         Flask /api/analysis/medical_resources
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ads_medical_stat;
CREATE TABLE ads_medical_stat (
    province           STRING COMMENT '省份名称',
    year               INT    COMMENT '年份',
    total_institutions BIGINT COMMENT '医疗机构总数',
    total_beds         BIGINT COMMENT '床位总数',
    total_doctors      BIGINT COMMENT '执业医师总数',
    total_nurses       BIGINT COMMENT '注册护士总数'
)
COMMENT 'ADS层 — 全国各省份年度医疗资源汇总'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE ads_medical_stat
SELECT
    province,
    year,
    SUM(medical_health_institutions) AS total_institutions,
    SUM(medical_health_beds)         AS total_beds,
    SUM(licensed_assistant_physicians) AS total_doctors,
    SUM(registered_nurses)           AS total_nurses
FROM dwd_medical_resource
GROUP BY province, year
ORDER BY province, year;

-- 核验: ADS 行数=310，DWD 行数=310（未压缩，仅列裁剪）
SELECT COUNT(*) AS ads_row_count FROM ads_medical_stat;
SELECT * FROM ads_medical_stat LIMIT 10;
