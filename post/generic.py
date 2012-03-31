from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from mathcontent.forms import MathContentSmallForm

from post.models import Post


class PostGenericRelation(generic.GenericRelation):
    def __init__(self, **kwargs):
        super(PostGenericRelation, self).__init__(Post, **kwargs)

    def get_content_type_id(self):
        return ContentType.objects.get_for_model(self.model).pk
    
        
    def contribute_to_class(self, cls, name):
        super(PostGenericRelation, self).contribute_to_class(cls, name)
        
        class Descriptor(generic.ReverseGenericRelatedObjectsDescriptor):
            def __get__(slf, instance, instance_type=None):
                manager = super(Descriptor, slf).__get__(instance=instance, instance_type=instance_type)
                manager.get_post_form = MathContentSmallForm
                manager.get_content_type_id = self.get_content_type_id
                return manager
                
        setattr(cls, self.name, Descriptor(self))
        
