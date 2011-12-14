from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404

from folder.models import Folder

def view(request, path=u''):
    # moze li se hardkodirati dobivanje root-a?
    folder = get_object_or_404(Folder, parent__isnull=True)
    
    P = filter(None, path.split('/'))
    data = folder.get_template_data_from_path(P, u'', 0, request.user)
    if not data:
        raise Http404

    data['path'] = path + '/' if path else ''
    data['tasks'] = data['tasks'].select_related('author')
    
    return render_to_response('folder_detail.html', 
            data,
        context_instance=RequestContext(request))
