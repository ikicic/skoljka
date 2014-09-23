/*
  Things to do after running this SQL:
    1) Refresh profile diff distribution (which also recalculates solved_count).
*/

ALTER TABLE userprofile_userprofile DROP COLUMN show_solution_task;

/* Convert old solution ratings to new ones. */
SET @solution_content_type = (
  SELECT id
    FROM django_content_type
    WHERE name = 'solution' AND app_label = 'solution' AND model = 'solution'
  );
UPDATE rating_vote
  SET value = IF(value >= 3, 2, 1)
  WHERE content_type_id = @solution_content_type;
UPDATE rating_score S
  SET S.sum = (
    SELECT SUM(V.value)
    FROM rating_vote V
    WHERE V.object_id = S.object_id AND V.content_type_id = S.content_type_id
  ), S.count = (
    SELECT COUNT(V.value)
    FROM rating_vote V
    WHERE V.object_id = S.object_id AND V.content_type_id = S.content_type_id
  )
  WHERE S.content_type_id = @solution_content_type;
UPDATE solution_solution S
  SET correctness_avg = IFNULL((
      SELECT SUM(value) / COUNT(*)
      FROM rating_vote V
      WHERE V.object_id = S.object_id AND V.content_type_id = S.content_type_id
    ), 0)
  WHERE S.status = 3;
UPDATE activity_action
  SET action_object_cache = IF(action_object_cache >= 3, 2, 1)
  WHERE type=220 AND subtype=0;

ALTER TABLE usergroup_usergroup CHANGE member_count cache_member_count INT;
