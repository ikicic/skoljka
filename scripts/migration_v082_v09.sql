source scripts/migration_utils.sql

call AddColumnUnlessExists('task_task', 'cache_file_attachment_thumbnail_url',
        'VARCHAR(150) NOT NULL AFTER cache_file_attachment_url');
call AddColumnUnlessExists('task_task', 'is_lecture', 'TINYINT NOT NULL DEFAULT 0');
call AddColumnUnlessExists('task_task', 'lecture_folder_id', 'INT NULL AFTER is_lecture');
call AddForeignKeyUnlessExists('task_task', 'lecture_folder_id', 'folder_folder');
call AddColumnUnlessExists('task_task', 'lecture_video_url', 'VARCHAR(200) NOT NULL AFTER is_lecture');

