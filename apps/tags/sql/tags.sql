/* used for /tags/ (list of all tags with task count for each tag) */
CREATE INDEX `tags_taggeditem_0` ON `tags_taggeditem` (`content_type_id`, `tag_id`);
