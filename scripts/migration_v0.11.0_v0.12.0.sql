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
