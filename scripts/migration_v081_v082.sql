ALTER TABLE competition_competition ADD COLUMN scoreboard_freeze_date DATETIME NOT NULL AFTER url_path_prefix;
UPDATE competition_competition SET scoreboard_freeze_date = end_date;

ALTER TABLE competition_competition ADD COLUMN evaluator_version INT NOT NULL DEFAULT 1 AFTER scoreboard_freeze_date;
UPDATE competition_competition SET evaluator_version = 0;

ALTER TABLE competition_competition ADD COLUMN fixed_task_score INT NOT NULL DEFAULT 0 AFTER evaluator_version;

ALTER TABLE competition_team ADD COLUMN cache_score_before_freeze INT NOT NULL DEFAULT 0 AFTER cache_score;
ALTER TABLE competition_team ADD COLUMN cache_max_score_after_freeze INT NOT NULL DEFAULT 0 AFTER cache_score_before_freeze;

ALTER TABLE competition_team ADD INDEX competition_team_score (cache_score);
ALTER TABLE competition_team ADD INDEX competition_team_frozen_score (cache_score_before_freeze);

ALTER TABLE competition_competitiontask CHANGE COLUMN correct_result descriptor VARCHAR(255) NOT NULL;
