from __future__ import unicode_literals
from django.utils.six.moves.builtins import str
from django.utils.six import with_metaclass
# -*- coding: utf-8 -*-

from django.db import models
from django.utils.text import slugify
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields

from scheduler.models.utils import get_model_bases

class CalendarManager(models.Manager):

    def get_or_create_calendar_for_object(self, obj, distinction=None, name=None):

        try:
            return self.get_calendar_for_object(obj, distinction)
        except Calendar.DoesNotExist:
            if name is None:
                calendar = Calendar(name=str(obj))
            else:
                calendar = Calendar(name=name)
            calendar.slug = slugify(calendar.name)
            calendar.save()
            calendar.create_relation(obj, distinction)
            return calendar

    def get_calendar_for_object(self, obj, distinction=None):

        calendar_list = self.get_calendars_for_object(obj, distinction)
        if len(calendar_list) == 0:
            raise Calendar.DoesNotExist("Calendar does not exist.")
        elif len(calendar_list) > 1:
            raise AssertionError("More than one calendars were found.")
        else:
            return calendar_list[0]

    def get_calendars_for_object(self, obj, distinction=None):

        ct = ContentType.objects.get_for_model(obj)
        if distinction:
            dist_q = models.Q(calendarrelation__distinction = distinction)
        else:
            dist_q = models.Q()
        return self.filter(dist_q, calendarrelation__object_id=obj.id, calendarrelation__content_type=ct)


@python_2_unicode_compatible
class Calendar(with_metaclass(models.base.ModelBase, *get_model_bases())):

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    objects = CalendarManager()

    def __str__(self):
        return self.name

    @property
    def events(self):
        return self.event_set

    def occurrences_after(self, after=None):
        return self.events.all().occurrences_after(after)

    def create_relation(self, obj, distinction=None):
        return CalendarRelation.objects.create_relation(self, obj, distinction)

class CalendarRelationManager(models.Manager):
    def create_relation(self, calendar, content_object, distinction = None):
        cr = CalendarRelation(
            calendar=calendar,
            distinction=distinction,
            content_object=content_object
        )
        cr.save()
        return cr

@python_2_unicode_compatible
class CalendarRelation(with_metaclass(models.base.ModelBase, *get_model_bases())):

    calendar = models.ForeignKey(Calendar)
    content_type=models.ForeignKey(ContentType)
    object_id = models.IntegerField()
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    distinction = models.CharField(max_length = 20, null=True)

    objects = CalendarRelationManager()

    def __str__(self):
        return '%s - %s' %( self.calendar, self.content_object )