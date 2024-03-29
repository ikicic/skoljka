from hashlib import md5

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import get_callable
from django.db import models

from skoljka.activity.action import remove, replace_or_add
from skoljka.rating.models import Score, Vote

AVERAGE = 1
SUM = 2

# po uzoru na https://github.com/dcramer/django-ratings


class RatingManager(models.Manager):
    def __init__(self, instance, field):
        """
        on_update callback arguments:
            (object instance, field_name, old_value, new_value)
        """
        self.instance = instance
        self.field = field
        self.field_name = field.field_name
        self.content_type = None

    def get_query_set(self, *args, **kwargs):
        return Vote.objects.get_query_set(*args, **kwargs).filter(
            object_id=self.instance.id,
            content_type=self.get_content_type(),
            key=self.field.key,
        )

    def get_content_type(self):
        if self.content_type is None:
            self.content_type = ContentType.objects.get_for_model(self.instance)
        return self.content_type

    def get_average(self):
        # used only for type == AVERAGE
        return getattr(self.instance, self.field_name)

    ##################
    # template helpers
    def get_range_and_titles(self):
        return zip(range(1, self.field.range), self.field.titles[1:])

    def get_star_split(self):
        return '' if self.field.range == 5 else ' {split:%d}' % (self.field.range / 5)

    # end template helpers
    ##################

    def get_vote_for_user(self, user):
        if not user.is_authenticated():
            return None
        try:
            return Vote.objects.get(
                object_id=self.instance.pk,
                content_type=self.get_content_type(),
                key=self.field.key,
                user=user,
            )
        except Vote.DoesNotExist:
            return None

    # TODO: optimizirati, ovo radi nepotrebne upite
    def update(self, user, value):
        value = int(value)
        score, created = Score.objects.get_or_create(
            object_id=self.instance.pk,
            content_type=self.get_content_type(),
            key=self.field.key,
        )
        vote, created = Vote.objects.get_or_create(
            object_id=self.instance.pk,
            content_type=self.content_type,
            key=self.field.key,
            user=user,
            defaults={'value': value},
        )

        if created:
            score.count += 1
        else:
            score.sum -= vote.value
            vote.value = value

        # TODO: pametnije ovo napraviti
        if value == 0:
            score.count -= 1
            # vote.delete() # don't delete yet, first remove the Activity
        else:
            score.sum += vote.value
            vote.save()

        score.save()

        if self.field.type == AVERAGE:
            field_value = 0 if score.count == 0 else float(score.sum) / score.count
        else:  # SUM
            field_value = score.sum

        old_field_value = getattr(self.instance, self.field_name, 0)
        setattr(self.instance, self.field_name, field_value)
        self.instance.save()

        if self.field.on_update:
            # automatically cache the function pointer itself, don't search
            # for the function every time
            self.field.on_update = get_callable(self.field.on_update)
            self.field.on_update(
                self.instance, self.field_name, old_field_value, field_value
            )

        if self.field.action_type:
            authors_group_id = (
                hasattr(self.instance, 'author_id')
                and self.instance.author.get_profile().private_group_id
            )
            if value == 0:
                remove(
                    user,
                    self.field.action_type[0],
                    action_object=vote,
                    target=self.instance,
                    group_id=authors_group_id,
                )
            else:
                replace_or_add(
                    user,
                    self.field.action_type,
                    action_object=vote,
                    target=self.instance,
                    group_id=authors_group_id,
                )

        if value == 0:
            vote.delete()  # ok, now delete

        return field_value


class RatingCreator(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, type=None):
        if instance is None:
            return self.field
            # raise AttributeError('Can only be accessed via an instance.')
        return RatingManager(instance, self.field)

    def __set__(self, instance, value):
        setattr(instance, self.field_name, float(value))


# u slucaju da treba i druge podatke cacheati, pogledaj
# https://gist.github.com/718687
# https://code.djangoproject.com/ticket/5929


class RatingField(models.FloatField):
    def __init__(self, *args, **kwargs):
        self.range = kwargs.pop('range', 5)
        self.titles = kwargs.pop('titles', range(1, self.range + 1))
        self.type = kwargs.pop('type', AVERAGE)
        self.action_type = kwargs.pop('action_type', None)
        self.on_update = kwargs.pop('on_update', None)
        if 'default' not in kwargs:
            kwargs['default'] = 0
        super(RatingField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        self.name = name
        self.key = md5(name).hexdigest()

        if self.type == AVERAGE:
            self.avg_field = models.FloatField(default=0)
            self.field_name = '%s_avg' % name
            cls.add_to_class(self.field_name, self.avg_field)
        else:  # self.type == SUM
            self.sum_field = models.IntegerField(default=0)
            self.field_name = '%s_sum' % name
            cls.add_to_class(self.field_name, self.sum_field)

        setattr(cls, name, RatingCreator(self))

    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("Object not set")
        return RatingManager(instance=instance, model=model, field=self)
