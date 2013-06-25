# (type, subtype)

TASK_ADD = (100, 1)                         # public    DONE
FILE_ADD = (100, 2)                         # public    DONE

SOLUTION_SEND = 200
SOLUTION_SUBMIT = (SOLUTION_SEND, 1)        # public    DONE
SOLUTION_AS_SOLVED = (SOLUTION_SEND, 2)     # public    DONE
SOLUTION_TODO = (SOLUTION_SEND, 3)          # public    DONE

SOLUTION_AS_OFFICIAL = (210, 0)             # public    NOT DONE

SOLUTION_RATE = (220, 0)    # public, solution.author   NOT DONE

# target=related_object, action_object=post, group=replied comment's author
POST_SEND = (300, 1)        # DONE

GROUP_CHANGE = 400
GROUP_ADD = (GROUP_CHANGE, 1)       # group     DONE
GROUP_LEAVE = (GROUP_CHANGE, 2)     # group     DONE

action_label = {
    TASK_ADD: ('label-success', 'Novi zadatak'),
    FILE_ADD: ('label-success', 'Nova datoteka'),
    SOLUTION_SUBMIT: ('label-info', 'Rješenje'),
    SOLUTION_AS_OFFICIAL: ('label-info', u'Službeno rješenje'),
}



# Comments on solution have to cache more than one information:
# Solution author_id > username > Task id > name > author_id.
# Not really a best solution, but this it way
# will be easier to escape >, using skoljka.utils.xss
POST_SEND_CACHE_SEPARATOR = u'>'

