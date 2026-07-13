-- ============================================================
-- MySQL 数据资源目录初始化脚本
-- 数据库: health_portal
-- 用途: 登记所有数据资源，记录来源、规模、状态和安全等级
-- 对应: Project13 指南 §5.6 + CONTRACT.md
-- ============================================================

CREATE DATABASE IF NOT EXISTS health_portal
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE health_portal;

-- 数据资源目录表
CREATE TABLE IF NOT EXISTS data_resource (
    resource_id    INT AUTO_INCREMENT PRIMARY KEY COMMENT '资源编号',
    resource_name  VARCHAR(200)  NOT NULL COMMENT '资源名称',
    resource_type  VARCHAR(100)  NOT NULL COMMENT '资源分类（医疗资源/健康统计/健康产业/气象环境/互联网公开信息）',
    department     VARCHAR(200)  DEFAULT '' COMMENT '来源部门',
    source_type    VARCHAR(50)   NOT NULL COMMENT '来源方式（下载/API/网页采集/模拟/人工整理）',
    file_format    VARCHAR(20)   DEFAULT 'CSV' COMMENT '文件格式',
    storage_location VARCHAR(500) DEFAULT '' COMMENT '本地/VM 存储路径',
    hdfs_path      VARCHAR(500)  DEFAULT '' COMMENT 'HDFS 路径',
    record_count   INT           DEFAULT 0 COMMENT '记录数量',
    update_frequency VARCHAR(50) DEFAULT '按需更新' COMMENT '更新频率',
    update_time    DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '最近更新时间',
    security_level ENUM('公开','内部','受限') NOT NULL DEFAULT '公开' COMMENT '安全等级',
    resource_status ENUM('待导入','已导入','已清洗','已发布','已停用') NOT NULL DEFAULT '待导入' COMMENT '资源状态',
    description    TEXT          COMMENT '资源说明',
    created_at     DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_resource_type (resource_type),
    INDEX idx_security_level (security_level),
    INDEX idx_status (resource_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据资源目录';

-- ============================================================
-- 初始数据：注册 5 类核心数据资源
-- (INSERT 语句由各模块清洗脚本在运行时生成具体记录数)
-- 以下为模板，实际 record_count / update_time 在清洗后填入
-- ============================================================

INSERT INTO data_resource (resource_name, resource_type, department, source_type, file_format,
    storage_location, hdfs_path, record_count, update_frequency, update_time,
    security_level, resource_status, description)
VALUES
('医疗机构数据',       '医疗资源',     '国家卫健委/地方卫健委', '下载/人工整理', 'CSV',
 'data/clean/medical_institutions.csv',  '/health_portal/clean/medical/medical_institutions.csv',  0, '按需更新', NOW(),
 '公开', '待导入', '全国及地区医疗机构数量、床位、医生、护士等资源统计数据。'),

('健康统计数据',       '健康统计',     '国家卫健委统计公报/国家统计局', '下载/人工整理', 'CSV',
 'data/clean/health_statistics.csv',     '/health_portal/clean/health_statistics/health_statistics.csv', 0, '按需更新', NOW(),
 '公开', '待导入', '年度/地区卫生健康统计指标，含医疗机构、床位、卫生人员等关键数据。'),

('健康产业数据',       '健康产业',     '国家药监局/国家统计局', '查询/人工整理', 'CSV',
 'data/clean/health_industry.csv',       '/health_portal/clean/industry/health_industry.csv',           0, '按需更新', NOW(),
 '公开', '待导入', '药品、医疗器械、医药制造等健康产业公开注册信息与行业指标。'),

('气象环境数据',       '气象环境',     '国家气象科学数据中心',   '下载/API',       'CSV',
 'data/clean/weather_environment.csv',   '/health_portal/clean/weather/weather_environment.csv',        0, '按需更新', NOW(),
 '公开', '待导入', '城市月度气温、湿度、降水、风速等地面气象观测数据。'),

('门户内容数据',       '互联网公开信息', '中国政府网/中国疾控中心', '网页采集',       'CSV',
 'data/clean/portal_contents.csv',       '/health_portal/clean/internet/portal_contents.csv',           0, '按需更新', NOW(),
 '公开', '待导入', '从中国政府网和中国疾控中心采集的新闻公告、政策资讯、健康知识等内容。');
