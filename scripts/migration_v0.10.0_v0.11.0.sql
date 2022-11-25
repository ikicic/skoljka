source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'public_scoreboard', 'SMALLINT NOT NULL DEFAULT 1 AFTER show_solutions');
call AddColumnUnlessExists('competition_competitiontask', 'cache_new_activities_count', 'INT NOT NULL DEFAULT 0 AFTER cache_admin_solved_count');
call ResizeVarcharIfShorter('competition_chain', 'category', 200);
