from skoljka.competition.decorators import competition_view
from skoljka.competition.evaluator import get_evaluator
from skoljka.utils.decorators import response

__all__ = ['rules']


@competition_view()
@response('competition_rules.html')
def rules(request, competition, data):
    evaluator = get_evaluator(competition.evaluator_version)
    types = evaluator.get_variable_types()
    # Class object is a callable, so wrap it with another function. If the
    # lambda was simply written as "lambda: x", all the values would have the
    # same x.
    data['variable_types'] = [(lambda y=x: y) for x in types]
    data['help_authors_general'] = evaluator.help_authors_general()
    return data
