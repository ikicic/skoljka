UPDATE `django_site`
    SET `domain` = 'www.skoljka.org', `name` = 'www.skoljka.org';

/* The password is 'a' */
INSERT INTO `auth_user` VALUES (
    1, 'arhiva', '', '', 'skoljka@mnm.hr',
    'pbkdf2_sha256$10000$yMWdq1JG0YYR$2pAO7cu1RzhFMXrms0GSp5Y0gUJdc5/GV1kSQWMUg00=',
    1, 1, 1, NOW(), NOW());
INSERT INTO `auth_group` VALUES (1, 'arhiva');
INSERT INTO `auth_user_groups` VALUES (1, 1, 1);

/* FIXME: this will throw warnings and stop the execution of this sql file! */
INSERT INTO `userprofile_userprofile`
    (`id`, `user_id`, `private_group_id`, `cache_group_ids`) VALUES
    (1, 1, 1, '1');
