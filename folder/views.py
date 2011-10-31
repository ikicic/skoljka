from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404

from folder.models import Folder
from search.utils import searchTasks

def folderView(request, path=u''):
    # moze li se hardkodirati dobivanje root-a?
    folder = get_object_or_404(Folder, parent__isnull=True)
    
    P = filter( None, path.split('/') )
    data = folder.get_template_data_from_path( P, u'' )
    if not data:
        raise Http404

    data['path'] = path + '/' if path else ''    
        
    return render_to_response('folder_detail.html', {
            'data' : data
        },
        context_instance=RequestContext(request),
    )
