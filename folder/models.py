from django.db import models
from django.db.models import Q
from django.contrib.contenttypes import generic
from django.template.defaultfilters import slugify

from model_utils.managers import InheritanceManager
from taggit.managers import TaggableManager

from permissions.constants import VIEW
from permissions.models import PerObjectGroupPermission
#from permissions.models import PerObjectUserPermission
from search.utils import search_tasks
from utils.tags import tag_list_to_html
from utils.string_operations import list_strip

# TODO: hm, DRY? ovo se ponavlja i u task
class FolderManager(InheritanceManager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            return super(FolderManager, self).get_query_set().filter(
                  Q(hidden=False)
#                | Q(user_permissions__user=user, user_permissions__permission_type=permission_type)
                | Q(group_permissions__group__user=user, group_permissions__permission_type=permission_type))
        else:
            return super(FolderManager, self).get_query_set().filter(hidden=False)


class Folder(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)
    parent = models.ForeignKey('self', blank=True, null=True)
    tag_filter = models.CharField(max_length=256, blank=True)

    hidden = models.BooleanField(default=False)
#    user_permissions = generic.GenericRelation(PerObjectUserPermission)
    group_permissions = generic.GenericRelation(PerObjectGroupPermission)
    objects = FolderManager();

    def __unicode__(self):
        return "%s - [%s]" % (self.name, self.tag_filter)

    @staticmethod
    def _path_part_to_html(name, path):
        return u'<li><a href="/folder%s/">%s</a></li>' % (path, name)
    @staticmethod
    def _html_tree_node(name, path, depth):
        return u'<div style="padding-left:%dpx">&raquo; <a href="/folder%s/">%s</a></div>\n' % ((depth - 1) * 10, path, name)
        
    def tag_list_html(self):
        return tag_list_to_html(self.tag_filter)
        

    #SPEED: optimizirati queryje ovdje?
    def get_template_data(self, path, depth, user):
        return {
            'name': self.name,
            'tag_list_html': tag_list_to_html(self.tag_filter),
            'child': [{'name': x.name, 'tag_list_html': x.tag_list_html, 'slug': x.slug} for x in Folder.objects.for_user(user, VIEW).filter(parent=self).distinct()],
            'tasks': search_tasks(tags=self.tag_filter, user=user, show_hidden=True),
            'path_html': Folder._path_part_to_html(self.name, path),
            'menu_folder_tree': '', #Folder._html_tree_node(self.name, path, depth) if self.parent else u'',
        }
        
    #SPEED: optimizirati?
    #TODO: listu zamijeniti necim primjerenijim za parametar P
    #TODO: menu_folder_tree pretvoriti u u''.join(), a ne +=
    def _get_template_data_from_path(self, P, path, depth, user):
        if not P:
            data = self.get_template_data(path, depth, user)
            for child in data['child']:
                data['menu_folder_tree'] += Folder._html_tree_node(child['name'], '%s/%s' % (path, child['slug']), depth + 1)

            return data
            
        menu_folder_tree = ''
        T = None

        for x in Folder.objects.for_user(user, VIEW).filter(parent=self).distinct():
            menu_folder_tree += Folder._html_tree_node(x.name, '%s/%s' % (path, x.slug), depth + 1)
            if x.slug == P[0]:
                T = x.get_template_data_from_path(P[1:], '%s/%s' % (path, x.slug), depth + 1, user)
                if not T:
                    return None
                    
                T['path_html'] = Folder._path_part_to_html(self.name, path) + " &raquo; " + T['path_html']
                T['menu_folder_tree'] = menu_folder_tree + T['menu_folder_tree']
                menu_folder_tree = ''
                    
                
        if T is not None:
            T['menu_folder_tree'] += menu_folder_tree
            return T
            
        return None
    
    def get_template_data_from_path(self, *args, **kwargs):
        """Polymorphically call a deriving class member function"""
        return Folder.objects.select_subclasses().get(id=self.id)._get_template_data_from_path(*args, **kwargs)
    

   
        
        
class FolderCollection(Folder):
    structure = models.TextField()

    @staticmethod
    def _parse_child(child):
        T = list_strip(child.split('/'), remove_empty=False)
        if len(T) == 1:
            data = [T[0], tag_list_to_html(T[0]), T[0], slugify(T[0])]
        elif len(T) == 2:
            data = [T[0], tag_list_to_html(T[1]), T[1], slugify(T[0])]
        else:
            data = [T[0], tag_list_to_html(T[1]), T[1], slugify(T[2])]
        return dict(zip(['name', 'tag_list_html', 'tags', 'slug'], data))
        
    
    #TODO(ikicic): uljepsati i pojasniti kod
    #TODO: optimizirati! (mozda i serializirati za sql)
    #TODO: menu_folder_tree pretvoriti u u''.join(), a ne +=
    def _get_template_data_from_path(self, P, path, depth, user):
        # Nije moguce postavljati posebna prava za pojedine
        # subfoldere FolderCollection-a.
    
        structure = []
        for G in list_strip(self.structure.split('@')):
            levels = []
            for L in list_strip(G.split('|')):
                levels.append([FolderCollection._parse_child(C) for C in list_strip(L.split(';'))])
            structure.append(levels)
        
        tree = []
        output_full_tags = u''
        output_children = []
        output_path_html = u''
        any = False
        for G in structure:         # for each group
            k = 0
            current_path = path
            tree_end = []
            
            # k == len(P) is hack
            while k <= len(P) and k < len(G):    # levels
                next = None
                tree_end2 = []
                for C in G[k]:                  # for each child
                    if next is None:
                        tree.append(Folder._html_tree_node(C['name'], '%s/%s' % (current_path, C['slug']), k + depth + 1))
                        if k < len(P) and P[k] == C['slug']:
                            next = C
                    else:
                        tree_end2.append(Folder._html_tree_node(C['name'], '%s/%s' % (current_path, C['slug']), k + depth + 1))
                tree_end = tree_end2 + tree_end
                
                if next is None:
                    break
                else:
                    k += 1
                    current_path += '/' + next['slug']
                    output_full_tags += ',' + next['tags']
                    output_path_html += ' &raquo; ' + Folder._path_part_to_html(next['name'], path)
            tree.extend(tree_end)
            
            if k == len(P):     # k will never be greater than len(P)
                if k < len(G):
                    output_children.extend(G[k])
                any = True      # url is ok
                
        if not any:
            return None         # url is not ok
        return {
            'name': self.name,
            'tag_list_html': tag_list_to_html( output_full_tags ),
            'child': output_children,
            'tasks': search_tasks(tags=output_full_tags, user=user, show_hidden=True),
            'path_html': output_path_html,
            'menu_folder_tree': u''.join(tree),
        }
        
        
    #TODO: izbrisati sljedecu funkciju, ostavljam za svaki slucaj sada
    # (ova funkcija vjerojatno ne radi bas... neuspjeli pokusaj prepravljanja)
    def old_get_template_data_from_path(self, P, path, depth):
        base_path = path;

        # groups divided by char @
        #   levels divided by char |
        #     children divided by char ;
        any = False
        PP = P[:]
        output_children = []
        output_full_tags = u''
        output_path_html = u''
        output_tree = []
        output_depth = depth
        output_chain = []
        for G in list_strip(self.structure.split('@')):
            full_tags = self.tag_filter
            path_html = Folder._path_part_to_html( self.name, path )
            P = PP[:]
            
            useless_group = False
            current_depth = depth + 1
            tree = []
            levels = list_strip(G.split('|'))
            for L in levels:
                children = list_strip(L.split(';'))
                
                # this way children info is remembered
                if not P:
                    break
                    
                found = False
                for child in children:
                    C = FolderCollection._parse_child( child )
                    tree.append(Folder._html_tree_node(C['name'], '%s/%s' % (path, C['slug']), current_depth))
                    if C['slug'] == P[0]:
                        full_tags += "," + C['tags']
                        path += '/' + C['slug']
                        path_html += " &raquo; " + Folder._path_part_to_html(C['name'], path)
                        current_depth += 1
                        
                        found = True
                        break

                if not found:
                    useless_group=True
                    break
                    
                # else found
                P = P[1:]
                children = []  # ...if this is last level
            
            if not useless_group:
                any = True
                output_children.extend( children )
                output_path_html = path_html
                output_full_tags = full_tags
                output_tree.extend(tree)
                output_depth = current_depth - 2
              
        if not any:
            return None
        return {
            'name': self.name,
            'tag_list_html': tag_list_to_html( output_full_tags ),
            'child': [ FolderCollection._parse_child( x ) for x in output_children ],
            'tasks': search_tasks(tags=output_full_tags),
            'path_html': output_path_html,
            'menu_folder_tree': u''.join(output_tree),
            'depth': output_depth,
        }
