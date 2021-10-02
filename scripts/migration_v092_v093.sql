source scripts/migration_utils.sql

ALTER TABLE `competition_chain` MODIFY `name` VARCHAR(200);
ALTER TABLE `competition_chain` MODIFY `category` VARCHAR(100);

call AddColumnUnlessExists('competition_competition', 'task_categories_trans', 'VARCHAR(255) NOT NULL DEFAULT "" AFTER team_categories');
