source scripts/migration_utils.sql

ALTER TABLE competition_competitiontask MODIFY chain_id INT NULL;

DELIMITER //
CREATE PROCEDURE update_competition_team_columns()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS
        WHERE column_name='team_type'
        and table_name='competition_team'
        and table_schema=DATABASE()
        )
    THEN
        ALTER TABLE competition_team
                ADD COLUMN team_type INT NOT NULL DEFAULT 0 AFTER is_test;
        UPDATE competition_team SET team_type = IF(`is_test`, 1, 0);
        ALTER TABLE competition_team DROP COLUMN is_test;
    END IF;
END //
DELIMITER ;
CALL update_competition_team_columns();
DROP PROCEDURE update_competition_team_columns;

call AddColumnUnlessExists('competition_teammember', 'is_selected', 'TINYINT NOT NULL DEFAULT 1');
call AddColumnUnlessExists('competition_competition', 'min_admin_solved_count', 'INT NOT NULL DEFAULT 0');
call AddColumnUnlessExists('competition_chain', 'cache_is_verified', 'TINYINT NOT NULL DEFAULT 1');
call AddColumnUnlessExists('competition_competitiontask', 'cache_admin_solved_count', 'INT NOT NULL DEFAULT 0');
