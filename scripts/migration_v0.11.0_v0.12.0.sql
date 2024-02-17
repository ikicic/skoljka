source scripts/migration_utils.sql

CREATE TABLE IF NOT EXISTS `competition_chainteam` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `chain_id` int(11) NOT NULL,
  `team_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `chain_id` (`chain_id`,`team_id`),
  KEY `competition_chainteam_9bfe773a` (`chain_id`),
  KEY `competition_chainteam_fcf8ac47` (`team_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

call AddColumnUnlessExists('competition_chain', 'restricted_access', 'TINYINT NOT NULL DEFAULT 0 AFTER unlock_mode');
call AddColumnUnlessExists('competition_chain', 'close_minutes', 'INT NOT NULL DEFAULT 0 AFTER unlock_minutes');
call DropColumnIfExists('task_task', 'prerequisites');
call DropColumnIfExists('task_task', 'solution_settings');
DELETE FROM `permissions_objectpermission` WHERE `permission_type` = 6;
