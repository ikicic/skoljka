ALTER TABLE folder_folder ADD COLUMN structure LONGTEXT NOT NULL;
UPDATE folder_folder F JOIN folder_foldercollection FC ON F.id = FC.folder_ptr_id SET F.structure = FC.structure;
DROP TABLE folder_foldercollection;

ALTER TABLE folder_folder ADD COLUMN parent_index INT NOT NULL DEFAULT 0 AFTER parent_id;
ALTER TABLE folder_folder ADD COLUMN cache_path VARCHAR(1000) NOT NULL;
ALTER TABLE folder_folder ADD COLUMN cache_ancestor_ids VARCHAR(255) NOT NULL;

ALTER TABLE permissions_perobjectgrouppermission RENAME TO permissions_objectpermission;

ALTER TABLE folder_folder ADD COLUMN author_id INT NOT NULL;
ALTER TABLE folder_folder ADD INDEX folder_folder_45845435 (author_id);
