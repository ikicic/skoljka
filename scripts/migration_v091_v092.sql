source scripts/migration_utils.sql

call AddColumnUnlessExists('post_post', 'extra', 'INT NOT NULL DEFAULT 0');
call AddIndexUnlessExists('post_post', 'post_post_extra', 'content_type_id, object_id, extra')

