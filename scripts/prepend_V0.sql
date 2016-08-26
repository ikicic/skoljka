UPDATE `mathcontent_mathcontent` SET
    `text` = CONCAT('%V0\n', `text`),
    `html` = NULL
    WHERE `text` NOT LIKE '|%V0%' ESCAPE '|';
