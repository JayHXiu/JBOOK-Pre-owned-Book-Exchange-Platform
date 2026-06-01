-- JBOOK - MySQL 数据库初始化
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `booktrade`
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `booktrade`;

DROP TABLE IF EXISTS `behavior_log`;
DROP TABLE IF EXISTS `daily_report`;
DROP TABLE IF EXISTS `message`;
DROP TABLE IF EXISTS `order_info`;
DROP TABLE IF EXISTS `collect`;
DROP TABLE IF EXISTS `sell_book`;
DROP TABLE IF EXISTS `book_base`;
DROP TABLE IF EXISTS `category`;
DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
    `user_id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(64) NOT NULL,
    `password` VARCHAR(128) NOT NULL,
    `nickname` VARCHAR(64) NOT NULL DEFAULT '',
    `role` TINYINT NOT NULL DEFAULT 0,
    `register_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `last_login` DATETIME NULL,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB COMMENT='用户表';

CREATE TABLE `category` (
    `cat_id` INT NOT NULL AUTO_INCREMENT,
    `cat_name` VARCHAR(64) NOT NULL,
    `parent_id` INT NULL,
    PRIMARY KEY (`cat_id`),
    KEY `idx_parent` (`parent_id`),
    CONSTRAINT `fk_cat_parent` FOREIGN KEY (`parent_id`) REFERENCES `category` (`cat_id`)
) ENGINE=InnoDB COMMENT='图书类目';

CREATE TABLE `book_base` (
    `book_id` INT NOT NULL AUTO_INCREMENT,
    `isbn` VARCHAR(20) NOT NULL,
    `book_name` VARCHAR(200) NOT NULL,
    `author` VARCHAR(128) NOT NULL DEFAULT '',
    `publisher` VARCHAR(128) NOT NULL DEFAULT '',
    `pub_year` INT NULL,
    `original_price` DECIMAL(10,2) NOT NULL DEFAULT 0,
    `cat_id` INT NOT NULL,
    `book_desc` TEXT,
    `tags` VARCHAR(256) NOT NULL DEFAULT '',
    PRIMARY KEY (`book_id`),
    UNIQUE KEY `uk_isbn` (`isbn`),
    KEY `idx_book_name` (`book_name`),
    KEY `idx_cat` (`cat_id`),
    CONSTRAINT `fk_book_cat` FOREIGN KEY (`cat_id`) REFERENCES `category` (`cat_id`)
) ENGINE=InnoDB COMMENT='图书基础信息';

CREATE TABLE `sell_book` (
    `sell_id` INT NOT NULL AUTO_INCREMENT,
    `book_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `second_price` DECIMAL(10,2) NOT NULL,
    `quality` TINYINT NOT NULL DEFAULT 3,
    `cover_img` VARCHAR(512) NOT NULL DEFAULT '',
    `view_count` INT NOT NULL DEFAULT 0,
    `collect_count` INT NOT NULL DEFAULT 0,
    `consult_count` INT NOT NULL DEFAULT 0,
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status` TINYINT NOT NULL DEFAULT 1,
    `is_hot` TINYINT(1) NOT NULL DEFAULT 0,
    `is_anomaly` TINYINT(1) NOT NULL DEFAULT 0,
    `audit_status` TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (`sell_id`),
    KEY `idx_book` (`book_id`),
    KEY `idx_user` (`user_id`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_sell_book` FOREIGN KEY (`book_id`) REFERENCES `book_base` (`book_id`),
    CONSTRAINT `fk_sell_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB COMMENT='在售图书';

CREATE TABLE `collect` (
    `collect_id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `sell_id` INT NOT NULL,
    `collect_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`collect_id`),
    UNIQUE KEY `uk_user_sell` (`user_id`, `sell_id`),
    CONSTRAINT `fk_collect_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`),
    CONSTRAINT `fk_collect_sell` FOREIGN KEY (`sell_id`) REFERENCES `sell_book` (`sell_id`)
) ENGINE=InnoDB COMMENT='收藏';

CREATE TABLE `order_info` (
    `order_id` VARCHAR(32) NOT NULL,
    `buyer_id` INT NOT NULL,
    `seller_id` INT NOT NULL,
    `sell_id` INT NOT NULL,
    `deal_price` DECIMAL(10,2) NOT NULL,
    `order_status` TINYINT NOT NULL DEFAULT 0,
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `finish_time` DATETIME NULL,
    PRIMARY KEY (`order_id`),
    KEY `idx_buyer` (`buyer_id`),
    KEY `idx_seller` (`seller_id`),
    KEY `idx_sell` (`sell_id`),
    CONSTRAINT `fk_order_buyer` FOREIGN KEY (`buyer_id`) REFERENCES `user` (`user_id`),
    CONSTRAINT `fk_order_seller` FOREIGN KEY (`seller_id`) REFERENCES `user` (`user_id`),
    CONSTRAINT `fk_order_sell` FOREIGN KEY (`sell_id`) REFERENCES `sell_book` (`sell_id`)
) ENGINE=InnoDB COMMENT='订单';

CREATE TABLE `behavior_log` (
    `log_id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NULL,
    `sell_id` INT NOT NULL,
    `action_type` TINYINT NOT NULL,
    `stay_time` INT NOT NULL DEFAULT 0,
    `action_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`log_id`),
    KEY `idx_user` (`user_id`),
    KEY `idx_sell` (`sell_id`),
    KEY `idx_action_time` (`action_time`),
    CONSTRAINT `fk_log_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`),
    CONSTRAINT `fk_log_sell` FOREIGN KEY (`sell_id`) REFERENCES `sell_book` (`sell_id`)
) ENGINE=InnoDB COMMENT='行为日志';

CREATE TABLE `message` (
    `msg_id` INT NOT NULL AUTO_INCREMENT,
    `sender_id` INT NOT NULL,
    `receiver_id` INT NOT NULL,
    `sell_id` INT NULL,
    `content` TEXT NOT NULL,
    `is_read` TINYINT(1) NOT NULL DEFAULT 0,
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`msg_id`),
    CONSTRAINT `fk_msg_sender` FOREIGN KEY (`sender_id`) REFERENCES `user` (`user_id`),
    CONSTRAINT `fk_msg_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB;

CREATE TABLE `daily_report` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `report_date` DATE NOT NULL,
    `new_users` INT NOT NULL DEFAULT 0,
    `new_sells` INT NOT NULL DEFAULT 0,
    `orders_done` INT NOT NULL DEFAULT 0,
    `total_views` INT NOT NULL DEFAULT 0,
    `report_json` JSON,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date` (`report_date`)
) ENGINE=InnoDB COMMENT='每日报表';

SET FOREIGN_KEY_CHECKS = 1;
