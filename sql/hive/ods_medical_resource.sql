-- ============================================================
-- ODS 层：全国省级医疗资源原始数据（外部表）
-- 数据源：national_provincial_medical_resources_2014_2023.csv
-- HDFS : /health_portal/raw/medical/
-- 行数 : 310 (31 省 × 10 年)
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ods_medical_resource;
CREATE EXTERNAL TABLE ods_medical_resource (
    record_id                           STRING  COMMENT '记录唯一编号 (CN-省份代码-年份)',
    year                                STRING  COMMENT '数据年份',
    province_code                       STRING  COMMENT '省级行政区代码',
    province                            STRING  COMMENT '省份名称',
    medical_health_institutions         STRING  COMMENT '医疗卫生机构总数(个)',
    hospitals                           STRING  COMMENT '医院数量(个)',
    primary_healthcare_institutions     STRING  COMMENT '基层医疗卫生机构数量(个)',
    specialized_public_health_institutions STRING COMMENT '专业公共卫生机构数量(个)',
    medical_health_beds                 STRING  COMMENT '医疗卫生机构床位总数(张)',
    hospital_beds                       STRING  COMMENT '医院床位数(张)',
    primary_healthcare_beds             STRING  COMMENT '基层医疗卫生机构床位数(张)',
    health_technicians                  STRING  COMMENT '卫生技术人员数量(人)',
    licensed_assistant_physicians       STRING  COMMENT '执业(助理)医师数量(人)',
    registered_nurses                   STRING  COMMENT '注册护士数量(人)',
    permanent_population                STRING  COMMENT '年末常住人口(人)',
    beds_per_1000_people                STRING  COMMENT '每千人医疗床位数(张)',
    physicians_per_1000_people          STRING  COMMENT '每千人医师数(人)',
    nurses_per_1000_people              STRING  COMMENT '每千人注册护士数(人)',
    institutions_per_10000_people       STRING  COMMENT '每万人医疗卫生机构数(个)',
    hospital_beds_share                 STRING  COMMENT '医院床位占比',
    primary_institution_share           STRING  COMMENT '基层机构占比',
    source                              STRING  COMMENT '数据来源URL',
    update_date                         STRING  COMMENT '数据采集日期'
)
COMMENT 'ODS层 — 全国省级医疗资源原始数据'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/health_portal/raw/medical/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- 验证
SELECT COUNT(*) AS row_count FROM ods_medical_resource;
SELECT * FROM ods_medical_resource LIMIT 5;
