source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'team_categories', 'VARCHAR(255) NOT NULL DEFAULT ""');
call AddColumnUnlessExists('competition_competition', 'show_solutions', 'TINYINT(1) NOT NULL DEFAULT 0');
call AddColumnUnlessExists('competition_team', 'category', 'INT NOT NULL DEFAULT 0');
