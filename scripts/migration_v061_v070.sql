ALTER TABLE folder_folder ADD COLUMN structure LONGTEXT NOT NULL;
UPDATE folder_folder F JOIN folder_foldercollection FC ON F.id = FC.folder_ptr_id SET F.structure = FC.structure;
DROP TABLE folder_foldercollection;

ALTER TABLE folder_folder ADD COLUMN parent_index INT NOT NULL DEFAULT 0 AFTER parent_id;
ALTER TABLE folder_folder ADD COLUMN cache_path VARCHAR(1000) NOT NULL;
ALTER TABLE folder_folder ADD COLUMN cache_ancestor_ids VARCHAR(255) NOT NULL;

ALTER TABLE permissions_perobjectgrouppermission RENAME TO permissions_objectpermission;

ALTER TABLE folder_folder ADD COLUMN author_id INT NOT NULL;
ALTER TABLE folder_folder ADD INDEX folder_folder_45845435 (author_id);
UPDATE folder_folder SET author_id = 1;


ALTER TABLE userprofile_userprofile DROP COLUMN birthday;
ALTER TABLE userprofile_userprofile DROP COLUMN city;
ALTER TABLE userprofile_userprofile DROP COLUMN country;
ALTER TABLE userprofile_userprofile DROP COLUMN quote;
ALTER TABLE userprofile_userprofile DROP COLUMN website;
ALTER TABLE userprofile_userprofile ADD COLUMN show_unsolved_task_solutions TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN evaluator TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN hide_solution_min_diff DOUBLE NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN show_solution_task TINYINT(1) NOT NULL DEFAULT 1;