from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from pagination.paginator import InfinitePaginator
from taggit.utils import parse_tags

from task.models import Task, SimilarTask
from task.forms import TaskForm, TaskAdvancedForm

from permissions.constants import ALL, EDIT, VIEW, EDIT_PERMISSIONS
from permissions.utils import get_permissions_for_object_by_id
from recommend.utils import task_event
from search.utils import update_search_cache
from solution.models import Solution
from solution.views import get_user_solved_tasks
from mathcontent.forms import MathContentForm
from mathcontent.latex import export_header, export_task, export_footer
from mathcontent.models import MathContent

import os, sys, codecs

# TODO: promijeniti nacin na koji se Task i MathContent generiraju.
# vrijednosti koje ne ovise o samom formatu se direktno trebaju
# postaviti na vrijednosti iz forme

@transaction.commit_on_success
@permission_required('task.add_advanced')
def advanced_new(request):
    if request.method == 'POST':
        task_form = TaskAdvancedForm(request.POST)
        math_content_form = MathContentForm(request.POST)
        
        if task_form.is_valid() and math_content_form.is_valid():
            task_template = task_form.save(commit=False)
            math_content_template = math_content_form.save(commit=False)            
            
            from collections import defaultdict
            dictionary = defaultdict(unicode)

            from xml.dom.minidom import parseString
            from xml.dom.minidom import Node
            dom = parseString(math_content_template.text.encode('utf-8'))
            # Xml -> <info> ... </info>
            
            for x in dom.firstChild.childNodes:
                if x.nodeType == Node.TEXT_NODE:
                    continue

                print x
                if x.nodeName != 'content':
                    value = x.nodeValue or ''
                    if x.firstChild:
                        value += x.firstChild.nodeValue or ''
                    dictionary[x.nodeName] = value
                    print (u'Postavljam varijablu "%s" na "%s"' % (x.nodeName, x.nodeValue)).encode('utf-8')

                if x.nodeName == 'content':
                    print (u'Dodajem zadatak "%s" s tagovima "%s"' % (task_template.name % dictionary, task_form.cleaned_data['_tags'] % dictionary)).encode('utf-8')
                    value = x.nodeValue or ''
                    if x.firstChild:
                        value += x.firstChild.nodeValue or ''
                    math_content = MathContent()
                    math_content.text = value     # should be safe
                    math_content.save()
                    print 'uspio dodati math_content'
                
                    task = Task()
                    task.name = task_template.name % dictionary
                    task.author = request.user
                    task.content = math_content
# TODO: automatizirati .hidden: (vidi TODO na vrhu funkcije)
                    task.hidden = task_template.hidden
                    task.save()

                    tags = parse_tags(task_form.cleaned_data['_tags'] % dictionary)
                    task.tags.set(*tags)
                    update_search_cache(task, [], tags)
                
            return HttpResponseRedirect('/task/new/finish/')
    else:
        task_form = TaskAdvancedForm()
        math_content_form = MathContentForm()

    return render_to_response( 'task_new.html', {
                'forms': [task_form, math_content_form],
                'action_url': request.path,
                'advanced': True,
            }, context_instance=RequestContext(request),
        )


################################################
# ovo je stara verzija, sa starim formatom

# TODO: maknuti debug s vremenom
def _advanced_new_parse(s, dictionary):
    print 'primio', s
    s = s % dictionary
    print 'vracam', s
    return s

@permission_required('task.add_advanced')
def old_advanced_new(request):
    if request.method == 'POST':
        task_form = TaskAdvancedForm(request.POST)
        math_content_form = MathContentForm(request.POST)
        
        if task_form.is_valid() and math_content_form.is_valid():
            task_template = task_form.save(commit=False)
            math_content_template = math_content_form.save(commit=False)            
            
            contents = math_content_template.text.split('@@@@@')
            contents = [x.strip() for x in contents]
            
            dictionary = dict()
            
            print contents
            print len(contents)
            for k in xrange(len(contents)):
                print 'k=%d' % k
                content = contents[k].strip()
                new_vars = content.find('###')
                if new_vars != -1:
                    for key, var in [x.split('=') for x in content[:new_vars].split('|')]:
                        dictionary[key.strip()] = var
                        print u'Postavljam varijablu "%s" na "%s"' % (key.strip(), var)
                    content = content[new_vars + 3:].strip()
                
                if not content:     # skip empty tasks
                    continue
                    
                math_content = MathContent()
                math_content.text = content
                math_content.save()
                print 'uspio dodati math_content'
                
                task = Task()
                task.name = _advanced_new_parse(task_template.name, dictionary)
                task.author = request.user
                task.content = math_content
# TODO: automatizirati .hidden: (vidi TODO na vrhu funkcije)
                task.hidden = task_template.hidden
                task.save()

                tags = parse_tags(_advanced_new_parse(task_form.cleaned_data['_tags'], dictionary))
                task.tags.set(*tags)
                update_search_cache(task, [], tags)
                
            return HttpResponseRedirect('/task/new/finish/')
    else:
        task_form = TaskAdvancedForm()
        math_content_form = MathContentForm()

    return render_to_response( 'task_new.html', {
                'forms': [task_form, math_content_form],
                'action_url': request.path,
                'advanced': True,
            }, context_instance=RequestContext(request),
        )

# kraj starog koda
#########################################################


@login_required
def new(request, task_id=None):
    if task_id:
        task = get_object_or_404(Task, pk=task_id)
        math_content = task.content
        old_tags = list(task.tags.values_list('name', flat=True))
        edit = True
    else:
        task = math_content = None
        old_tags = []
        edit = False
        
    if request.method == 'POST':
        task_form = TaskForm(request.POST, instance=task)
        math_content_form = MathContentForm(request.POST, instance=math_content)
        
        if task_form.is_valid() and math_content_form.is_valid():
            task = task_form.save(commit=False)
            math_content = math_content_form.save()
            
            if not edit:
                task.author = request.user

            task.content = math_content
            task.save()
            
            # Required for django-taggit:
            task_form.save_m2m()
            update_search_cache(task, old_tags, task.tags.values_list('name', flat=True))
            
            if edit:
                filename = os.path.normpath(os.path.join(settings.PROJECT_ROOT, 'media/pdf/task%d.pdf' % task.id))
                if os.path.exists(filename):
                    os.remove()
            
            # TODO: izbrisati task_new_finish.html i url
            #return HttpResponseRedirect('/task/%d/' % task.id if edit else '/task/new/finish/')
            return HttpResponseRedirect('/task/%d/' % task.id)
    else:
        task_form = TaskForm(instance=task)
        math_content_form = MathContentForm(instance=math_content)
 
    return render_to_response( 'task_new.html', {
                'forms': [task_form, math_content_form],
                'action_url': request.path,
                'edit': edit,
                'task': task,
            }, context_instance=RequestContext(request),
        )
        
def task_list(request):
    tasks = Task.objects.for_user(request.user, VIEW).select_related('author').distinct()
    # treba mi LEFT JOIN ON (task_task.id = solution_solution.task_id AND solution_solution.author_id = ##)
    # sada se umjesto toga koristi .cache_additional_info()
    # (slicno za tag-ove)
        
    return render_to_response( 'task_list.html', {
                'tasks' : tasks,
                'submitted_tasks' : get_user_solved_tasks(request.user),
            }, context_instance=RequestContext(request),
        )

def detail(request, id):
    task = get_object_or_404(Task, id=id)
    content_type = ContentType.objects.get_for_model(Task)

    try:
        solution = request.user.is_authenticated() and Solution.objects.filter(author=request.user, task=task)[:1][0]
    except (Solution.DoesNotExist, IndexError):
        solution = None

    if task.author == request.user or request.user.is_staff:
        perm = ALL
    else:
        perm = get_permissions_for_object_by_id(request.user, task.id, content_type)
        
    if not task.hidden:
        perm.append(VIEW)

    # TODO: nekakav drugi signal
    if VIEW not in perm:
        raise Http404

    # ovo ce ici preko C++ skripte za pocetak
    # task.update_similar_tasks(1)
    
    if request.user.is_authenticated():
        task_event(request.user, task, 'view')
        
    # TODO: DRY content_type
    return render_to_response('task_detail.html', {
            'task': task,
            'can_edit': EDIT in perm,
            'can_edit_permissions': EDIT_PERMISSIONS in perm,
            'content_type': content_type,
            'solution': solution,
        }, context_instance=RequestContext(request))

def similar(request, id):
    task = get_object_or_404(Task, pk=id)
    
    # TODO: dovrsiti, ovo je samo tmp
    task.update_similar_tasks(1)
    if request.user.is_authenticated():
        task_event(request.user, task, 'view')
    
    
    similar_ids = list(SimilarTask.objects.filter(task=task).order_by('-score')[:6].values_list('similar_id', flat=True))
    print similar_ids
    similar = Task.objects.filter(id__in=similar_ids)
    
    return render_to_response('task_similar.html', {
            'task': task,
            'similar': similar,
        }, context_instance=RequestContext(request))

# TODO: not allowed message        
def detail_multiple(request, ids):
    ids = [int(x) for x in ids.split(',')]
    if not ids or 0 in ids:
        raise Http404
        
    tasks = Task.objects.for_user(request.user, VIEW).filter(id__in=ids).select_related('content').distinct()
    id_list = [str(x) for x in ids]
    return render_to_response('task_detail_multiple.html', {
                'tasks': tasks,
                'id_list': ', '.join(id_list),
                'id_list_ns': ','.join(id_list),
            }, context_instance=RequestContext(request))

def _export_to_latex(request, ids):
    ids = [int(x) for x in ids.split(',')]
    if not ids or 0 in ids:
        raise Http404
        
    tasks = Task.objects.for_user(request.user, VIEW).filter(id__in=ids).select_related('content').distinct()
    content = u''.join([export_task % {'title': x.name, 'content': x.content.convert_to_latex()} for x in tasks])
    return u'%s%s%s' % (export_header, content, export_footer)
    

# TODO: not allowed message
def export_to_latex(request, ids):
    return HttpResponse(content=_export_to_latex(request, ids), content_type='application/x-latex')

def export_to_pdf(request, ids):
    filename = os.path.normpath(os.path.join(settings.LOCAL_DIR, 'media/pdf/task' + ids))
    print 'filename: ', filename
    if not os.path.exists(filename + '.pdf'):
        f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
        f.write(_export_to_latex(request, ids))
        f.close()
        
        os.system('latex -output-directory=%s -interaction=batchmode %s.tex' % (os.path.dirname(filename), filename))
        os.system('dvipdfm -o %s %s' % (filename + '.pdf', filename))
        # os.remove(filename + '.tex')
        # os.remove(filename + '.log')
        # os.remove(filename + '.aux')
        # os.remove(filename + '.dvi')
        
    return HttpResponseRedirect('/media/pdf/task%s.pdf' % ids)