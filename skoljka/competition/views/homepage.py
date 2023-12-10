from skoljka.competition.decorators import competition_view
from skoljka.utils.decorators import response

__all__ = ['homepage']


@competition_view()
@response('competition_homepage.html')
def homepage(request, competition, data):
    return data
