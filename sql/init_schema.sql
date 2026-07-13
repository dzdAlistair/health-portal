-- 健康大数据门户业务库建表脚本
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
  `publish_date` date DEFAULT NULL COMMENT '发布日期',
  `status` tinyint DEFAULT 1 COMMENT '状态：1已发布 0草稿',
  `views` int DEFAULT 0 COMMENT '浏览量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`content_id`),
  KEY `idx_type_status` (`content_type`,`status`),
  KEY `idx_publish_date` (`publish_date`)
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