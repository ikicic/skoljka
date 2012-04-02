INSERT INTO `auth_user` VALUES (1, 'arhiva', '', '', 'skoljka@getaldic.org', 'sha1$ad2fa$faf1d0b3503195e230575e5543732cfd752fa64d', 1, 1, 1, NOW(), NOW());
INSERT INTO `auth_group` VALUES (1, 'arhiva');
INSERT INTO `auth_user_groups` VALUES (1, 1, 1);
INSERT INTO `userprofile_userprofile` VALUES (1, 1, '', NULL, '', '', '', '', 0, 0, NULL, 1, 0, 0.0, '');

UPDATE `django_site` SET `domain` = 'skoljka.no-ip.org', `name` = 'skoljka.no-ip.org'
