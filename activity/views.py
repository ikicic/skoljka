from activity.models import Action


def list(request):
    events = Action.objects.order_by('-id')
    return render_to_response('activity_list.html', {
            'events': events,
        }, context_instance=RequestContext(request))