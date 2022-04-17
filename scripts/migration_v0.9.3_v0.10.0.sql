source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'kind', 'SMALLINT NOT NULL DEFAULT 1 AFTER name');
call AddColumnUnlessExists('competition_submission', 'content_id', 'INT NULL AFTER result');
call AddForeignKeyUnlessExists('competition_submission', 'content_id', 'mathcontent_mathcontent');
call AddColumnUnlessExists('competition_submission', 'score', 'INT NULL DEFAULT 0 AFTER content_id');
call AddColumnUnlessExists('competition_submission', 'latest_unseen_admin_activity', 'DATETIME NOT NULL DEFAULT "2000-01-01" AFTER score');
