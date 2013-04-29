/*
  Don't forget to: (or automate...)
    1) run Folder migration admin action
    2) reset attachment file size
    3) run Solution refresh_detailed_status admin action.
    4) run UserProfile refresh_group_cache admin action.
*/

/* Structure */
DROP TABLE folder_foldercollection;

ALTER TABLE folder_folder CHANGE COLUMN slug short_name VARCHAR(128) NOT NULL;
UPDATE folder_folder SET short_name = name;

ALTER TABLE folder_folder ADD COLUMN editable TINYINT(1) NOT NULL DEFAULT 1 AFTER hidden;

ALTER TABLE folder_folder ADD COLUMN parent_index INT NOT NULL DEFAULT 0 AFTER parent_id;
ALTER TABLE folder_folder ADD COLUMN cache_ancestor_ids VARCHAR(255) NOT NULL;

ALTER TABLE folder_folder ADD COLUMN author_id INT NOT NULL;
ALTER TABLE folder_folder ADD INDEX folder_folder_45845435 (author_id);
UPDATE folder_folder SET author_id = 1;

ALTER TABLE folder_folder CHANGE COLUMN tag_filter cache_tags VARCHAR(256) NOT NULL;

ALTER TABLE mathcontent_attachment ADD COLUMN cache_file_size INT NOT NULL DEFAULT 0;

ALTER TABLE permissions_perobjectgrouppermission RENAME TO permissions_objectpermission;

ALTER TABLE task_task ADD COLUMN file_attachment_id INT NULL;
ALTER TABLE task_task ADD COLUMN cache_file_attachment_url VARCHAR(150) NOT NULL AFTER file_attachment_id;
ALTER TABLE task_task ADD COLUMN solvable TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE userprofile_userprofile DROP COLUMN birthday;
ALTER TABLE userprofile_userprofile DROP COLUMN city;
ALTER TABLE userprofile_userprofile DROP COLUMN country;
ALTER TABLE userprofile_userprofile DROP COLUMN quote;
ALTER TABLE userprofile_userprofile DROP COLUMN score;
ALTER TABLE userprofile_userprofile DROP COLUMN website;
ALTER TABLE userprofile_userprofile ADD COLUMN show_unsolved_task_solutions TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN evaluator TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN eval_sol_last_view DATETIME NOT NULL AFTER evaluator;
ALTER TABLE userprofile_userprofile ADD COLUMN hide_solution_min_diff DOUBLE NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN show_solution_task TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE userprofile_userprofile ADD COLUMN school_class INT NOT NULL DEFAULT 0;
ALTER TABLE userprofile_userprofile ADD COLUMN cache_group_ids VARCHAR(255) NOT NULL;

ALTER TABLE folder_folder_tasks ADD COLUMN position INT NOT NULL DEFAULT 0;


ALTER TABLE search_searchcache CHANGE COLUMN tag_string `key` VARCHAR(100) NOT NULL;

ALTER TABLE solution_solution ADD COLUMN detailed_status iNT DEFAULT 0 NOT NULL AFTER status;

/* Indices */

ALTER TABLE folder_folder ADD INDEX folder_folder_editable (editable);
ALTER TABLE search_searchcacheelement ADD INDEX search_searchcacheelement_tuple1 (object_id, content_type_id, cache_id);
ALTER TABLE search_searchcacheelement ADD INDEX search_searchcacheelement_tuple2 (cache_id, content_type_id);
ALTER TABLE solution_solution ADD INDEX solution_solution_tuple1 (detailed_status, date_created);
