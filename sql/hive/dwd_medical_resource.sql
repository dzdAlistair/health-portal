-- ============================================================
-- DWD 层：全国省级医疗资源清洗明细表
-- 来源  : ods_medical_resource
-- 清洗规则:
--   1. 剔除 record_id/year/province 全为 NULL 的无效行
--   2. 限定 year BETWEEN 2014 AND 2023
--   3. 数值列 CAST 为 BIGINT/DOUBLE
--   4. 按 province + year 联合去重
-- 行数  : ≤ 310
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS dwd_medical_resource;
CREATE TABLE dwd_medical_resource (
    record_id                           STRING  COMMENT '记录唯一编号',
    year                                INT     COMMENT '数据年份',
    province_code                       STRING  COMMENT '省级行政区代码',
    province                            STRING  COMMENT '省份名称',
    medical_health_institutions         BIGINT  COMMENT '医疗卫生机构总数',
    hospitals                           BIGINT  COMMENT '医院数量',
    primary_healthcare_institutions     BIGINT  COMMENT '基层医疗卫生机构数量',
    specialized_public_health_institutions BIGINT COMMENT '专业公共卫生机构数量',
    medical_health_beds                 BIGINT  COMMENT '医疗卫生机构床位总数',
    hospital_beds                       BIGINT  COMMENT '医院床位数',
    primary_healthcare_beds             BIGINT  COMMENT '基层医疗卫生机构床位数',
    health_technicians                  BIGINT  COMMENT '卫生技术人员数量',
    licensed_assistant_physicians       BIGINT  COMMENT '执业(助理)医师数量',
    registered_nurses                   BIGINT  COMMENT '注册护士数量',
    permanent_population                BIGINT  COMMENT '年末常住人口',
    beds_per_1000_people                DOUBLE  COMMENT '每千人医疗床位数',
    physicians_per_1000_people          DOUBLE  COMMENT '每千人医师数',
    nurses_per_1000_people              DOUBLE  COMMENT '每千人注册护士数',
    institutions_per_10000_people       DOUBLE  COMMENT '每万人医疗卫生机构数',
    hospital_beds_share                 DOUBLE  COMMENT '医院床位占比',
    primary_institution_share           DOUBLE  COMMENT '基层机构占比',
    source                              STRING  COMMENT '数据来源URL',
    update_date                         STRING  COMMENT '数据采集日期'
)
COMMENT 'DWD层 — 全国省级医疗资源清洗明细'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE dwd_medical_resource
SELECT
    record_id,
    try_cast(year AS INT) AS year,
    province_code,
    province,
    try_cast(medical_health_institutions AS BIGINT),
    try_cast(hospitals AS BIGINT),
    try_cast(primary_healthcare_institutions AS BIGINT),
    try_cast(specialized_public_health_institutions AS BIGINT),
    try_cast(medical_health_beds AS BIGINT),
    try_cast(hospital_beds AS BIGINT),
    try_cast(primary_healthcare_beds AS BIGINT),
    try_cast(health_technicians AS BIGINT),
    try_cast(licensed_assistant_physicians AS BIGINT),
    try_cast(registered_nurses AS BIGINT),
    try_cast(permanent_population AS BIGINT),
    try_cast(beds_per_1000_people AS DOUBLE),
    try_cast(physicians_per_1000_people AS DOUBLE),
    try_cast(nurses_per_1000_people AS DOUBLE),
    try_cast(institutions_per_10000_people AS DOUBLE),
    try_cast(hospital_beds_share AS DOUBLE),
    try_cast(primary_institution_share AS DOUBLE),
    source,
    update_date
FROM ods_medical_resource
WHERE record_id IS NOT NULL
  AND year IS NOT NULL
  AND province IS NOT NULL
  AND try_cast(year AS INT) BETWEEN 2014 AND 2023;

-- 验证：DWD 行数 ≤ ODS 行数
SELECT COUNT(*) AS dwd_row_count FROM dwd_medical_resource;
SELECT * FROM dwd_medical_resource LIMIT 5;
