from django.template.defaultfilters import slugify
from django.db import models
from taggit.managers import TaggableManager

from model_utils.managers import InheritanceManager

from search.utils import searchTasks
from utils.tags import tagListToHTML
from utils.string_operations import listStrip


class Folder(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child')
    tag_filter = models.CharField(max_length=256, blank=True)
    objects = InheritanceManager();

    def __unicode__(self):
        return "%s - [%s]" % (self.name, self.tag_filter)

    @staticmethod
    def _path_part_to_html(name, path):
        return "<a href=\"/folder%s/\">%s</a>" % (path, name)
        
    def tag_list_html(self):
        return tagListToHTML( self.tag_filter )

    #SPEED: optimizirati queryje ovdje?
    def get_template_data(self,path):
        return {
            'name': self.name,
            'tag_list_html': tagListToHTML( self.tag_filter ),
            'child': [ { 'name': x.name, 'tag_list_html': x.tag_list_html, 'slug': x.slug } for x in self.child.all() ],
            'tasks': searchTasks(tags=self.tag_filter),
            'path_html': Folder._path_part_to_html(self.name, path)
        }
        
    #SPEED: optimizirati?
    #TODO: listu zamijeniti necim primjerenijim za parametar P
    def _get_template_data_from_path(self,P,path):
        if not P:
            return self.get_template_data(path)
        for x in self.child.all():
            if x.slug == P[0]:
                T = x.get_template_data_from_path(P[1:], path + '/' + x.slug)
                if not T:
                    return None
                T['path_html'] = Folder._path_part_to_html(self.name, path) + " &raquo; " + T['path_html']
                return T
        return None
    
    def get_template_data_from_path(self,P,path):
        """Polymorphically call a deriving class member function"""
        return Folder.objects.select_subclasses().get(id=self.id)._get_template_data_from_path(P,path)
    

   
        
        
class FolderCollection(Folder):
    structure = models.TextField()

    @staticmethod
    def parseChild(child):
        T = listStrip(child.split('/'), removeEmpty=False)
        if len(T) == 1:
            data = [T[0], tagListToHTML(T[0]), T[0], slugify(T[0])]
        elif len(T) == 2:
            data = [T[0], tagListToHTML(T[1]), T[1], slugify(T[0])]
        else:
            data = [T[0], tagListToHTML(T[1]), T[1], slugify(T[2])]
        return dict(zip( ['name', 'tag_list_html', 'tags', 'slug'], data ))
        
    
    #TODO(ikicic): uljepsati i pojasniti kod
    #TODO(ikicic): replace list with something faster for P
    def _get_template_data_from_path(self,P,path):

        # groups divided by char @
        any = False
        PP = P[:]
        output_children = []
        output_full_tags = u''
        output_path_html = u''
        for G in listStrip(self.structure.split('@')):
            full_tags = self.tag_filter
            path_html = Folder._path_part_to_html( self.name, path )
            P = PP[:]
            
            useless_group=False
            for L in listStrip(G.split('|')):
                children = listStrip(L.split(';'))
                
                # this way children info is remembered
                if not P:
                    break
                    
                found = False
                for child in children:
                    C = FolderCollection.parseChild( child )
                    if C['slug'] == P[0]:
                        full_tags += "," + C['tags']
                        path += '/' + C['slug']
                        path_html += " &raquo; " + Folder._path_part_to_html( C['name'], path )
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
                
        if not any:
            return None
        return {
            'name': self.name,
            'tag_list_html': tagListToHTML( output_full_tags ),
            'child': [ FolderCollection.parseChild( x ) for x in output_children ],
            'tasks': searchTasks(tags=output_full_tags),
            'path_html': output_path_html
        }
