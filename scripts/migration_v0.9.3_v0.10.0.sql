source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'kind', 'SMALLINT NOT NULL DEFAULT 1 AFTER name');
call AddColumnUnlessExists('competition_submission', 'content_id', 'INT NULL AFTER result');
call AddForeignKeyUnlessExists('competition_submission', 'content_id', 'mathcontent_mathcontent');
