source scripts/migration_utils.sql

call AddColumnUnlessExists('competition_competition', 'kind', 'SMALLINT NOT NULL DEFAULT 1 AFTER name');
