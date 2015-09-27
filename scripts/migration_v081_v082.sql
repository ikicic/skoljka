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
ALTER TABLE competition_competitiontask ADD COLUMN comment_id INT NOT NULL DEFAULT 0 AFTER chain_position;

DELIMITER //
CREATE PROCEDURE add_competitiontask_empty_comments()
BEGIN
    read_loop: LOOP
        SET @id = (SELECT id FROM competition_competitiontask
                             WHERE comment_id = 0 LIMIT 1);

        SELECT 'id', @id;
        IF (@id IS NULL) THEN
            LEAVE read_loop;
        END IF;
        INSERT INTO mathcontent_mathcontent (`text`, `html`) VALUES ('', '');
        UPDATE competition_competitiontask
            SET comment_id=(SELECT LAST_INSERT_ID()) WHERE id=@id LIMIT 1;
    END LOOP read_loop;
END //
DELIMITER ;
CALL add_competitiontask_empty_comments();
DROP PROCEDURE add_competitiontask_empty_comments;
ALTER TABLE `competition_competitiontask` ADD CONSTRAINT `comment_id_refs_id_74d1988` FOREIGN KEY (`comment_id`) REFERENCES `mathcontent_mathcontent` (`id`);

ALTER TABLE competition_chain ADD COLUMN cache_ctask_comments_info VARCHAR(255) NOT NULL AFTER bonus_score;
