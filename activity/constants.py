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
