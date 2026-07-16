CREATE TABLE IF NOT EXISTS `outbreak_thresholds` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `disease_label` VARCHAR(150) NOT NULL UNIQUE,
  `case_threshold` SMALLINT UNSIGNED NOT NULL DEFAULT 3,
  `rolling_window_days` SMALLINT UNSIGNED NOT NULL DEFAULT 7,
  `is_active` BOOLEAN NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `outbreak_thresholds_chk_1` CHECK (`case_threshold` >= 0),
  CONSTRAINT `outbreak_thresholds_chk_2` CHECK (`rolling_window_days` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
