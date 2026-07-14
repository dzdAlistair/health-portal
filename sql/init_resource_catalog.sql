-- ==============================================================
-- 文件名：init_resource_catalog.sql
-- 功能：健康门户MySQL库表结构初始化 + 业务基础测试数据初始化
-- 模块1：库表Schema（原init_schema.sql）
-- 模块2：分类/内容/资源基础测试数据（原init_data.sql）
-- 适用数据库：health_portal
-- ==============================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 创建业务数据库
CREATE DATABASE IF NOT EXISTS health_portal DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE health_portal;

-- --------------------------
-- 模块一：全业务表建表语句（原 init_schema.sql）
-- --------------------------
-- 1. 管理员用户表
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `user_id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password_hash` varchar(255) NOT NULL COMMENT '密码哈希',
  `role` varchar(20) DEFAULT 'admin' COMMENT '角色：super_admin/admin',
  `status` tinyint DEFAULT 1 COMMENT '状态：1正常 0禁用',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员用户表';

-- 2. 内容分类表
DROP TABLE IF EXISTS `content_category`;
CREATE TABLE `content_category` (
  `cate_id` int NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `cate_name` varchar(50) NOT NULL COMMENT '分类名称',
  `content_type` varchar(20) NOT NULL COMMENT '内容类型：news/policy/knowledge',
  `sort` int DEFAULT 0 COMMENT '排序',
  `status` tinyint DEFAULT 1 COMMENT '状态：1启用 0禁用',
  PRIMARY KEY (`cate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='内容分类表';

-- 3. 门户内容表
DROP TABLE IF EXISTS `portal_content`;
CREATE TABLE `portal_content` (
  `content_id` int NOT NULL AUTO_INCREMENT COMMENT '内容ID',
  `content_type` varchar(20) NOT NULL COMMENT '内容类型：news/policy/knowledge/application',
  `category_id` int DEFAULT NULL COMMENT '所属分类ID',
  `title` varchar(200) NOT NULL COMMENT '标题',
  `summary` varchar(500) DEFAULT NULL COMMENT '摘要',
  `content` text COMMENT '正文内容',
  `source` varchar(100) DEFAULT NULL COMMENT '来源',
  `source_url` varchar(300) DEFAULT NULL COMMENT '原文链接',
  `publishing_date` date DEFAULT NULL COMMENT '发布日期',
  `status` tinyint DEFAULT 1 COMMENT '状态：1已发布 0草稿',
  `views` int DEFAULT 0 COMMENT '浏览量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`content_id`),
  KEY `idx_type_status` (`content_type`,`status`),
  KEY `idx_publish_date` (`publishing_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='门户内容表';

-- 4. 应用中心表
DROP TABLE IF EXISTS `application_info`;
CREATE TABLE `application_info` (
  `app_id` int NOT NULL AUTO_INCREMENT COMMENT '应用ID',
  `app_name` varchar(100) NOT NULL COMMENT '应用名称',
  `app_desc` varchar(300) DEFAULT NULL COMMENT '应用描述',
  `app_icon` varchar(200) DEFAULT NULL COMMENT '图标路径',
  `app_url` varchar(300) NOT NULL COMMENT '应用跳转地址',
  `sort` int DEFAULT 0 COMMENT '排序',
  `status` tinyint DEFAULT 1 COMMENT '状态：1启用 0禁用',
  PRIMARY KEY (`app_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应用中心表';

-- 5. 资源分类表
DROP TABLE IF EXISTS `resource_category`;
CREATE TABLE `resource_category` (
  `cate_id` int NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `cate_name` varchar(50) NOT NULL COMMENT '分类名称',
  `sort` int DEFAULT 0 COMMENT '排序',
  `status` tinyint DEFAULT 1 COMMENT '状态：1启用 0禁用',
  PRIMARY KEY (`cate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源分类表';

-- 6. 数据资源目录表
DROP TABLE IF EXISTS `data_resource`;
CREATE TABLE `data_resource` (
  `resource_id` int NOT NULL AUTO_INCREMENT COMMENT '资源ID',
  `resource_name` varchar(100) NOT NULL COMMENT '资源名称',
  `resource_type` varchar(50) DEFAULT NULL COMMENT '资源类型',
  `category_id` int DEFAULT NULL COMMENT '所属分类ID',
  `department` varchar(100) DEFAULT NULL COMMENT '来源部门',
  `source_type` varchar(50) DEFAULT NULL COMMENT '获取方式：下载/API/网页采集/模拟',
  `file_format` varchar(20) DEFAULT NULL COMMENT '文件格式：CSV/JSON/XLSX',
  `storage_location` varchar(300) DEFAULT NULL COMMENT '本地存储路径',
  `hdfs_path` varchar(300) DEFAULT NULL COMMENT 'HDFS存储路径',
  `record_count` int DEFAULT 0 COMMENT '数据条数',
  `update_frequency` varchar(50) DEFAULT NULL COMMENT '更新频率',
  `update_time` datetime DEFAULT NULL COMMENT '最后更新时间',
  `security_level` varchar(20) DEFAULT '公开' COMMENT '安全等级：公开/内部/受限',
  `resource_status` varchar(20) DEFAULT '已发布' COMMENT '状态：已发布/草稿/下架',
  `description` text COMMENT '资源描述',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`resource_id`),
  KEY `idx_security_status` (`security_level`,`resource_status`),
  KEY `idx_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据资源目录表';

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------
-- 模块二：基础初始化测试数据（原 init_data.sql）
-- --------------------------
USE health_portal;

-- 1. 初始化内容分类
INSERT INTO `content_category` (`cate_name`, `content_type`, `sort`) VALUES
('行业动态', 'news', 1),
('政策文件', 'policy', 2),
('健康科普', 'knowledge', 3);

-- 2. 初始化资源分类
INSERT INTO `resource_category` (`cate_name`, `sort`) VALUES
('医疗资源', 1),
('健康统计', 2),
('健康产业', 3),
('气象环境', 4),
('互联网信息', 5);

-- 3. 测试门户内容（3条）
INSERT INTO `portal_content` (`content_type`, `category_id`, `title`, `summary`, `source`, `publishing_date`, `status`, `views`) VALUES
('news', 1, '2026年全国医疗资源总量持续增长', '国家卫健委发布最新数据，全国医疗机构数量同比增长3.2%，床位数突破900万张。', '国家卫健委', '2026-06-15', 1, 128),
('policy', 2, '“健康中国2030”规划中期评估报告发布', '报告显示健康中国建设各项指标稳步推进，公共卫生服务体系持续完善。', '国家卫健委', '2026-05-20', 1, 256),
('knowledge', 3, '夏季常见传染病预防指南', '夏季高温高湿，肠道传染病、中暑等高发，需注意饮食卫生与防暑降温。', '中国疾控中心', '2026-07-01', 1, 342);

-- 4. 测试数据资源（3条）
INSERT INTO `data_resource` (`resource_name`, `resource_type`, `category_id`, `source_type`, `file_format`, `record_count`, `security_level`, `resource_status`, `description`) VALUES
('全国医疗机构基础数据集', '结构化数据', 1, '公开数据下载', 'CSV', 35862, '公开', '已发布', '包含全国各级医疗机构的名称、地址、等级、床位等基础信息。'),
('全国居民健康统计年报', '统计数据', 2, '官方发布', 'XLSX', 1258, '公开', '已发布', '涵盖历年人口健康指标、慢性病患病率、医疗服务利用等统计数据。'),
('健康产业市场规模数据', '产业数据', 3, '公开数据下载', 'CSV', 86, '公开', '已发布', '包含医疗健康、养老、保健品等细分产业的市场规模与增速数据。');