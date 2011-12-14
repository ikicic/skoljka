from django.contrib.auth.models import User, Group
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

# TODO: (?) spojiti content_type i permission_type u jednu konstantu
# (npr. TASK_VIEW, TASK_EDIT, FOLDER_VIEW... koje bi primjerice bile jednake
# content_type * 10000 + permission_type) Ipak se radi o vrlo kompleksnom
# queryju, pa bi takva usteda koristila. No, moze se ugroziti DRY princip.

# TODO: ispitati moze li se user spojiti s grupama, tj. da se za svakog
# korisnika napravi jedna grupa, pa sve ide samo preko grouppermission-a.
# Time bi se maknuo jedan JOIN u upitima, a i prepolovili bi se svi kodovi
# vezani uz permission-e. (tako i tako grupe i korisnic moraju imati
# medjusobno razlicita imena)

class PerObjectGroupPermission(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    group = models.ForeignKey(Group)

# better not to take foreignkey to Permission    
    permission_type = models.IntegerField()

# TODO: treba li ovo? (unique provjeru treba napraviti u formi/fieldu, vidi permissions.edit)
    class Meta:
        unique_together = (('object_id', 'content_type', 'group', 'permission_type'),)
    
    
class PerObjectUserPermission(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    user = models.ForeignKey(User)

# better not to take foreignkey to Permission    
    permission_type = models.IntegerField()

# TODO: treba li ovo? (unique provjeru treba napraviti u formi/fieldu, vidi permissions.edit)
    class Meta:
        unique_together = (('object_id', 'content_type', 'user', 'permission_type'),)
