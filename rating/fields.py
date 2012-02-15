from django.db import models
from django.contrib.contenttypes.models import ContentType

from hashlib import md5

from rating.models import Score, Vote

# po uzoru na https://github.com/dcramer/django-ratings

class RatingManager(models.Manager):
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field
        self.content_type = None

    def get_content_type(self):
        if self.content_type is None:
            self.content_type = ContentType.objects.get_for_model(self.instance)
        return self.content_type

    def get_average(self):
        return getattr(self.instance, '%s_avg' % self.field.name)
        
    ##################
    # template helpers
    def get_range_and_titles(self):
        return zip(range(1, self.field.range + 1), self.field.titles)
        
    def get_star_split(self):
        return '' if self.field.range == 5 else ' {split:%d}' % (self.field.range / 5)
        
    # end template helpers
    ##################
        
    def get_vote_for_user(self, user):
        if not user.is_authenticated():
            return None
        try:
            return Vote.objects.get(object_id=self.instance.pk, content_type=self.get_content_type(), key=self.field.key, user=user)
        except Vote.DoesNotExist:
            return None


    # TODO: optimizirati, ovo radi nepotrebne upite
    def update(self, user, value):
        value = int(value)
        score, created = Score.objects.get_or_create(object_id=self.instance.pk, content_type=self.get_content_type(), key=self.field.key)
        vote, created = Vote.objects.get_or_create(object_id=self.instance.pk, content_type=self.content_type, key=self.field.key, user=user, defaults={'value': value})
        if created:
            score.count += 1
        else:
            score.sum -= vote.value
            vote.value = value
            
        # TODO: pametnije ovo napraviti
        if value == 0:
            score.count -= 1
            vote.delete()
        else:
            score.sum += vote.value
            vote.save()
        
        score.save()
        
        setattr(self.instance, '%s_avg' % self.field.name, 0 if score.count == 0 else float(score.sum) / score.count)
        self.instance.save()
        


class RatingCreator(object):
    def __init__(self, field):
        self.field = field
        self.avg_field_name = '%s_avg' % self.field.name

    def __get__(self, instance, type=None):
        if instance is None:
            return self.field
            #raise AttributeError('Can only be accessed via an instance.')
        return RatingManager(instance, self.field)

    def __set__(self, instance, value):
        setattr(instance, self.avg_field_name, float(value))

        
# u slucaju da treba i druge podatke cacheati, pogledaj
# https://gist.github.com/718687
# https://code.djangoproject.com/ticket/5929

class RatingField(models.FloatField):
    def __init__(self, *args, **kwargs):
        self.range = kwargs.pop('range', 5)
        self.titles = kwargs.pop('titles', range(1, self.range + 1))
        if 'default' not in kwargs:
            kwargs['default'] = 0
        super(RatingField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        self.name = name
        self.key = md5(name).hexdigest()
        self.avg_field = models.FloatField(default=0)
        cls.add_to_class('%s_avg' % name, self.avg_field)
        setattr(cls, name, RatingCreator(self))
        
    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("Object not set")
        return RatingManager(instance=instance, model=model, field=self)
