CREATE DATABASE IF NOT EXISTS `desktop_ai_companion`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `desktop_ai_companion`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `phone` VARCHAR(32) NOT NULL UNIQUE,
  `nickname` VARCHAR(64) NULL,
  `avatar_url` VARCHAR(255) NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `sms_codes` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `phone` VARCHAR(32) NOT NULL,
  `scene` VARCHAR(32) NOT NULL,
  `code_hash` VARCHAR(128) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `consumed_at` DATETIME NULL,
  `send_ip` VARCHAR(64) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_sms_codes_phone_scene` (`phone`, `scene`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `refresh_token_hash` VARCHAR(128) NOT NULL UNIQUE,
  `device_id` VARCHAR(128) NULL,
  `device_name` VARCHAR(128) NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_user_sessions_user_id` (`user_id`),
  CONSTRAINT `fk_user_sessions_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `membership_plans` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `plan_code` VARCHAR(64) NOT NULL UNIQUE,
  `plan_name` VARCHAR(64) NOT NULL,
  `price_fen` INT NOT NULL,
  `duration_days` INT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `benefits_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `user_memberships` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `plan_code` VARCHAR(64) NOT NULL,
  `status` VARCHAR(32) NOT NULL,
  `started_at` DATETIME NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `source_order_no` VARCHAR(64) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_user_memberships_user_id` (`user_id`),
  CONSTRAINT `fk_user_memberships_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `payment_orders` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `order_no` VARCHAR(64) NOT NULL UNIQUE,
  `user_id` BIGINT NOT NULL,
  `plan_code` VARCHAR(64) NOT NULL,
  `amount_fen` INT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `pay_channel` VARCHAR(32) NOT NULL DEFAULT 'wechat_native',
  `wechat_prepay_id` VARCHAR(128) NULL,
  `wechat_code_url` TEXT NULL,
  `wechat_transaction_id` VARCHAR(128) NULL,
  `paid_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_payment_orders_user_id` (`user_id`),
  CONSTRAINT `fk_payment_orders_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `payment_callbacks` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
  `provider` VARCHAR(32) NOT NULL,
  `event_type` VARCHAR(64) NOT NULL,
  `payload_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `membership_plans` (
  `plan_code`,
  `plan_name`,
  `price_fen`,
  `duration_days`,
  `status`,
  `benefits_json`
) VALUES
  (
    'free',
    '免费版',
    0,
    0,
    'active',
    JSON_OBJECT(
      'max_companions', 1,
      'daily_message_quota', 100,
      'monthly_message_quota', 3000,
      'model_access_level', 'free',
      'voice_access_level', 'free'
    )
  ),
  (
    'vip_monthly',
    'VIP 月卡',
    2900,
    30,
    'active',
    JSON_OBJECT(
      'max_companions', 3,
      'daily_message_quota', 300,
      'monthly_message_quota', 10000,
      'model_access_level', 'vip',
      'voice_access_level', 'vip'
    )
  ),
  (
    'svip_monthly',
    'SVIP 月卡',
    5900,
    30,
    'active',
    JSON_OBJECT(
      'max_companions', 10,
      'daily_message_quota', 1000,
      'monthly_message_quota', 30000,
      'model_access_level', 'svip',
      'voice_access_level', 'svip'
    )
  )
ON DUPLICATE KEY UPDATE
  `plan_name` = VALUES(`plan_name`),
  `price_fen` = VALUES(`price_fen`),
  `duration_days` = VALUES(`duration_days`),
  `status` = VALUES(`status`),
  `benefits_json` = VALUES(`benefits_json`);
