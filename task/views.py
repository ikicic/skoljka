from django import forms
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from pagination.paginator import InfinitePaginator

from task.models import Task
from task.forms import TaskForm, TaskAdvancedForm

from solution.models import Solution
from solution.views import get_user_solved_tasks
from mathcontent.forms import MathContentForm
from mathcontent.models import MathContent

def _advanced_new_parse(s, dictionary):
    print 'primio', s
    s = s % dictionary
    print 'vracam', s
    return s

#TODO(ikicic): error za zadatke bez teksta: @@@ (prazno) @@@
@login_required
def advanced_new(request):
    # dok permissions ne radi
    if request.user.username != 'ikicic':
        raise Http404

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
                task.save()

                task.tags.set(*parse_tags(_advanced_new_parse(task_form.cleaned_data['_tags'], dictionary)))
                
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


@login_required
def new(request, task_id=None):
    if task_id:
        task = get_object_or_404(Task, pk=task_id)
        math_content = task.content
        edit = True
    else:
        task = math_content = None
        edit = False
        
    if request.method == 'POST':
        task_form = TaskForm(request.POST,instance=task)
        math_content_form = MathContentForm(request.POST,instance=math_content)
        
        if task_form.is_valid() and math_content_form.is_valid():
            task = task_form.save(commit=False)
            math_content = math_content_form.save()
            
            if not edit:
                task.author = request.user

            task.content = math_content
            task.save()
            
            # Required for django-taggit:
            task_form.save_m2m()
            
            return HttpResponseRedirect('/task/new/finish/')
    else:
        task_form = TaskForm(instance=task)
        math_content_form = MathContentForm(instance=math_content)
 
    return render_to_response( 'task_new.html', {
                'forms': [task_form, math_content_form],
                'action_url': request.path,
            }, context_instance=RequestContext(request),
        )
        
def task_list(request):
    tasks = Task.objects.select_related()
        
    return render_to_response( 'task_list.html', {
                'tasks' : tasks,
                'submitted_tasks' : get_user_solved_tasks(request.user),
            }, context_instance=RequestContext(request),
        )
