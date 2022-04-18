source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'kind', 'SMALLINT NOT NULL DEFAULT 1 AFTER name');
call AddColumnUnlessExists('competition_submission', 'content_id', 'INT NULL AFTER result');
call AddForeignKeyUnlessExists('competition_submission', 'content_id', 'mathcontent_mathcontent');
call AddColumnUnlessExists('competition_submission', 'score', 'INT NULL DEFAULT 0 AFTER content_id');
call AddColumnUnlessExists('competition_submission', 'oldest_unseen_admin_activity', 'DATETIME NOT NULL DEFAULT "2000-01-01" AFTER score');
call AddColumnUnlessExists('competition_submission', 'oldest_unseen_team_activity', 'DATETIME NOT NULL DEFAULT "2000-01-01" AFTER score');

DROP PROCEDURE IF EXISTS rename_competition_submission_cache_is_correct;
DELIMITER //
CREATE PROCEDURE rename_competition_submission_cache_is_correct()
BEGIN
    IF EXISTS (
        SELECT * FROM information_schema.COLUMNS
        WHERE column_name='cache_is_correct'
        and table_name='competition_submission'
        and table_schema=DATABASE()
        )
    THEN
        UPDATE competition_submission S
            INNER JOIN competition_competitiontask C
            SET S.score = IF(S.cache_is_correct, C.score, S.score);
        ALTER TABLE competition_submission DROP COLUMN cache_is_correct;
    END IF;
END //
DELIMITER ;
CALL rename_competition_submission_cache_is_correct();
DROP PROCEDURE rename_competition_submission_cache_is_correct;


DROP PROCEDURE IF EXISTS rename_competitiontask_score;
DELIMITER //
CREATE PROCEDURE rename_competitiontask_score()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS
        WHERE column_name='max_score'
        and table_name='competition_competitiontask'
        and table_schema=DATABASE()
        )
    THEN
        ALTER TABLE competition_competitiontask CHANGE COLUMN `score` `max_score` INT NOT NULL DEFAULT 0;
    END IF;
END //
DELIMITER ;
CALL rename_competitiontask_score();
DROP PROCEDURE rename_competitiontask_score;
