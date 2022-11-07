source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'public_scoreboard', 'SMALLINT NOT NULL DEFAULT 1 AFTER show_solutions');
