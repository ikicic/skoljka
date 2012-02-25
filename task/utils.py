


def task_similarity(first, second):
    a = set(first.get_tag_ids())
    b = set(second.get_tag_ids())
    tag_sim = len(a & b)

    # difficulty similarity
    if first.difficulty_rating_avg == 0.0 or second.difficulty_rating_avg == 0.0:
        diff_sim = 0.1
    else:
        diff_sim = 1. / (1 + (first.difficulty_rating_avg - second.difficulty_rating_avg) ** 2)
    
    # total similarity
    return tag_sim * diff_sim
    