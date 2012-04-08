TASK_ADD = 101              # public    DONE

SOLUTION_SUBMIT = 201       # public    DONE
SOLUTION_AS_SOLVED = 202    # public    DONE
SOLUTION_TODO = 203         # public    DONE
SOLUTION_AS_OFFICIAL = 210  # public    NOT DONE
SOLUTION_RATE = 220         # public, solution.author   NOT DONE

POST_SEND = 301             # target=related_object, action_object=post, group=replied comment's author     DONE

GROUP_ADD = 401             # group     DONE
GROUP_LEAVE = 402           # group     DONE

action_label = {
    TASK_ADD: ('label-success', 'Novi zadatak'),
}



# Comments on solution have to cache more than one information:
# Solution author_id > username > Task id > name > author_id.
# Not really a best solution, but this it way
# will be easier to escape >, using skoljka.utils.xss
POST_SEND_CACHE_SEPARATOR = u'>'

