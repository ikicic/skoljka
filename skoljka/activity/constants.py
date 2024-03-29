﻿# (type, subtype)

TASK_ADD = (100, 1)
FILE_ADD = (100, 2)
LECTURE_ADD = (100, 3)

SOLUTION_SEND = 200
SOLUTION_SUBMIT = (SOLUTION_SEND, 1)
SOLUTION_AS_SOLVED = (SOLUTION_SEND, 2)
SOLUTION_TODO = (SOLUTION_SEND, 3)

SOLUTION_AS_OFFICIAL = (210, 0)  # NOT DONE

SOLUTION_RATE = (220, 0)  # solution.author   NOT DONE

# target=related_object, action_object=post, group=replied comment's author
# TODO: split comments for Tasks and for Solutions
POST_SEND = (300, 1)

GROUP_CHANGE = 400
GROUP_ADD = (GROUP_CHANGE, 1)  # group
GROUP_LEAVE = (GROUP_CHANGE, 2)  # group

COMPETITION_UPDATE_SUBMISSION_SCORE = (500, 1)

action_label = {
    TASK_ADD: ('label-success', "Novi zadatak"),
    FILE_ADD: ('label-success', "Nova datoteka"),
    LECTURE_ADD: ('label-success', "Novo predavanje"),
    SOLUTION_SUBMIT: ('label-info', u"Rješenje"),
    SOLUTION_AS_OFFICIAL: ('label-info', u"Službeno rješenje"),
}


# Comments on solution have to cache more than one information:
# Solution author_id > username > Task id > name > author_id.
# Not really a best solution, but this way it
# will be easier to escape >, using skoljka.utils.xss
POST_SEND_CACHE_SEPARATOR = u'>'
