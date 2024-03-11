from __future__ import unicode_literals
from django.utils.six.moves.builtins import str
from django.utils.six import with_metaclass
# -*- coding: utf-8 -*-

import heapq
from dateutil import rrule
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible 
from django.utils.formats import date_format
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType

from scheduler.settings import settings
from scheduler.models.utils import NextOccurrenceReplacer, OccurrenceReplacer, get_model_bases, SubclassingQuerySet
from scheduler.models.rules import Rule
from scheduler.models.calendars import Calendar

SLUG_DATE_FORMAT='%Y-%m-%d-%H-%M%z'
if not settings.USE_TZ:
    SLUG_DATE_FORMAT='%Y-%m-%d-%H-%M'

class EventListQuerySet(SubclassingQuerySet):

    def _resolve_slug(self, slug):
        split_slug = slug.split('-',1)
        when = None
        if len(split_slug) > 1:
            when = datetime.strptime(split_slug[1], SLUG_DATE_FORMAT)
        return split_slug[0], when

    def _deliver_slug(self, slug):
        pk, when = self._resolve_slug(slug)
        if self.query.high_mark \
            and self.query.high_mark-self.query.low_mark <= 1:
            self.query.clear_limits()
        event = next(iter(self.filter(pk=pk)))
        if when:
            return event.get_occurrence(when)
        return event

    #Need to override private method _clone, in order to
    #keep track of slug!
    def _clone(self):
        clone = super(EventListQuerySet, self)._clone()
        if hasattr(self, 'slug'):
            clone.slug = self.slug
        return clone

    def iterator(self):
        if hasattr(self,'slug'):
            slug = self.slug
            del self.slug
            return [self._deliver_slug(slug)]
        return super(EventListQuerySet, self).iterator()

    def get(self, *args, slug=None, **kwargs):
        if slug:
            return self._deliver_slug(slug)
        return super(EventListQuerySet, self).get(*args, **kwargs)

    def filter(self, *args, slug=None, **kwargs):
        if slug:
            self.slug=slug
        return super(EventListQuerySet, self).filter(*args, **kwargs)

    def exclude(self, *args, slug=None, **kwargs):
        if slug:
            pk, when = self._resolve_slug(slug)
            kwargs.setdefault('pk', pk)
            if when:
                kwargs.setdefault('start', when)
        return super(EventListQuerySet, self).exclude(*args, **kwargs)

    def occurrences_after(self, after=None, tzinfo=timezone.utc):
        if after is None:
            after = timezone.now()
        #NEED TO FILTER FOR SORCE-EVENT!
        group_events = self.model.objects.filter(
            rule__in=self.values_list('rule', flat=True).distinct(),
            cancelled=None, original_start=None, original_end=None
        ).exclude(
            rule__end_recurring_period__lte=after
        )
        occ_replacer = NextOccurrenceReplacer(self.exclude(
                cancelled=None, original_start=None, original_end=None
        ))
        source_events = self.filter(
            rule=None, end__gt=after
        )
        #This is a little hacky:
        #The second for is used ONLY as an assignment!
        #(By using this expression, just one loop is required!)
        occurrences = [
            (next(generator), generator)
            for event_group in group_events
            # generator = event_group._occurrences_after_generator(after)
            for generator in [
                event_group._occurrences_after_generator(after)
            ]
        ]
        #Taking care of rule=None events.
        occurrences += [
            (next(generator), generator)
            for event in self.filter(rule=None)
            # generator = event_group._occurrences_after_generator(after)
            for generator in [
                event._occurrences_after_generator(after)
            ]
        ]
        heapq.heapify(occurrences)

        while True:
            if len(occurrences) == 0:
                raise StopIteration

            generator = occurrences[0][1]

            try:
                next_occurence = heapq.heapreplace(occurrences, (next(generator), generator))[0]
            except StopIteration:
                next_occurence = heapq.heappop(occurrences)[0]
            for occ in occ_replacer.get_next_occurrences(next_occurence):
                yield occ

from datetime import datetime
class EventManager(models.Manager):

    def get_queryset(self):
        return EventListQuerySet(self.model)

    def event_group(self, source=None):
        return self.exclude(cancelled=None)

    def source_events(self):
        return self.filter(models.Q(cancelled=None) | models.Q(rule=None))

    def get_for_object(self, content_object, distinction=None):
        return EventRelation.objects.get_events_for_object(content_object, distinction, self)

class BaseEvent(with_metaclass(models.base.ModelBase, *get_model_bases())):
    content_type = models.ForeignKey(ContentType, editable=False, null=True)
    objects = EventManager()

    occurrence_subclasses = {}

    class Meta():
        abstract=True

    def save(self, *args, **kwargs):
        if not self.content_type:
            self.content_type=ContentType.objects.get_for_model(self.__class__)
        self.save_base(*args, **kwargs)

    def as_leaf_class(self):
        if self.content_type:
            model = self.content_type.model_class()
            if model == self.__class__:
                return self
            return model.objects.get(id=self.id)
        else:
            return self

#ONLY SUBCLASS EVENT!
#EventRelation NEEDS ForeignKey FROM NON-ABSTRACT CLASS!!!
@python_2_unicode_compatible
class Event(BaseEvent):
    original_start = models.DateTimeField(blank=True, null=True, editable=False)
    original_end = models.DateTimeField(blank=True, null=True, editable=False)
    start = models.DateTimeField()
    end = models.DateTimeField(help_text="The end time must be later than the start time.")
    cancelled = models.NullBooleanField(null=True, blank=True, default=False)

    rule = models.ForeignKey(Rule, null=True, blank=True)

    calendar = models.ForeignKey(Calendar, null=True, blank=True)

    class Meta():
        abstract=False

    @property
    def slug(self):
        if not hasattr(self,'_slug'):
            if self.pk==None and self.group_source.pk == None:
                return None
            pk = self.pk or self.group_source.pk
            #beware never to set _slug to None!
            self._slug = "%i-%s"%(pk, self.start.strftime(SLUG_DATE_FORMAT))
        return self._slug

    def save(self, *args, **kwargs):
        reset_saved = False
        if self.group_source == self:
            reset_saved = True
        elif not getattr(self.group_source, 'pk', None):
            self.group_source.save()

        super(Event, self).save(*args, **kwargs)
        if reset_saved:
            self.group_source = self

    def __init__(self, *args, **kwargs):
        if kwargs.get('rule', None) and not kwargs.get('cancelled', False) == None:
            kwargs['cancelled'] = None
            try:
                type(self).objects.get(rule=kwargs['rule'], cancelled=None)
            except type(self).DoesNotExist:
                if not kwargs['rule'].start_recurring_period:
                    kwargs['rule'].start_recurring_period = kwargs['start']
                    kwargs['rule'].save()
                kwargs.setdefault('original_start', kwargs['start'])
                kwargs.setdefault('original_end'  , kwargs['end']  )

        self.group_source = self

        super(Event, self).__init__(*args, **kwargs)
        if self.rule:
            self.event_group = type(self).objects.filter(rule=self.rule).exclude(cancelled=None)
        else:
            #this may blow up in our face!
            #need to save before pk exists.
            self.event_group = type(self).objects.filter(pk = self.pk)

    def __str__(self):
        #date_format default format is 'DATE_FORMAT'
        return '%s - %s%s' %(date_format(self.start), date_format(self.end), ", GROUP_SOURCE" if self.cancelled == None else "")

    def __lt__(self, other):
        return self.end < other.end

    def __gt__(self, other):
        return self.start > other.start

    #Need this WHAT FOR exactly?
    def __eq__(self, other):
        #Check weather same timeslot is occupied!
        return isinstance(other, Event) and self.start == other.start and self.end == other.end

    @property
    def duration(self):
        return self.end-self.start

    @property
    def seconds(self):
        return self.duration.total_seconds()

    @property
    def minutes(self):
        return float(self.seconds) / 60

    @property
    def hours(self):
        return float(self.seconds) / 3600

    @property
    def moved(self):
        return not (self.original_start == self.start and self.original_end == self.end)

    def move(self, new_start, new_end = None):
        #THIS IS NO YET WORKING!!!
        if False and type(new_start) == datetime.timedelta:
            new_end = self.end + new_start
            new_start = self.start + new_start
        self.end = new_end or new_start + (self.end - self.start)
        self.start = new_start
        self.save()

    def cancel(self):
        if self.cancelled == None:
            raise TypeError("source event can't be cancelled!")
        self.cancelled = True
        self.save()

    def uncancel(self):
        if self.cancelled:
            self.cancelled = False
            self.save()

    def _clone_model(self):
        new_kwargs = dict([(fld.name, getattr(self, fld.name)) for fld in self._meta.fields if fld.name != 'id'])
        return self.__class__(**new_kwargs)

    def get_occurrences(self, start, end):
        persisted_occurrences = self.event_group.filter(models.Q(end__gte=start, start__lte=end) | models.Q(original_end__gte=start, original_start__lte=end))
        occ_replacer = OccurrenceReplacer(persisted_occurrences)

        occurrences = self._get_occurrence_list(start, end)
        final_occurrences = []
        for occ in occurrences:
            if occ_replacer.has_occurrence(occ):
                p_occ = occ_replacer.get_occurrence(occ)
                if p_occ.start < end and p_occ.end >= start:
                    final_occurrences.append(p_occ)

            else:
                final_occurrences.append(occ)

        final_occurrences += occ_replacer.get_additional_occurrences(start, end)
        return final_occurrences

    def _get_occurrence_list(self, start, end):
        if self.rule is None:
            if self.start < end and self.end > start:
                return [self._create_occurrence(self.start)]
            else:
                return []

        occurrences = []
        if self.rule.end_recurring_period and self.rule.end_recurring_period < end:
            end = self.rule.end_recurring_period
        rule = self.get_rrule_object()
        occ_starts = rule.between(start-self.duration, end, inc=True)

        for start in occ_starts:
            end = start + self.duration
            #yield self._create_occurrence(start, end) #delete following lines, not needed?
            occurrence = self._create_occurrence(start, end)
            occurrences.append(occurrence)

        return occurrences

    def _create_occurrence(self, start, end=None):
        if end is None:
            end = start + self.duration
        ret = self.group_source._clone_model()

        ret.original_start = ret.start = start
        ret.original_end   = ret.end   = end
        ret.cancelled = False
        return ret

    def get_rrule_object(self):
        if self.rule is None:
            return None
        params = self.rule.get_params()
        frequency = self.rule.rrule_frequency()
        return rrule.rrule(frequency, dtstart = self.rule.start_recurring_period, **params)

    def get_occurrence(self, start, exact=False):
        ret = next(self.occurrences_after(start))
        if not exact:
            return ret
        elif ret.start == start:
            return ret

    def occurrences_after(self, after=None):
        if after is None:
            after = timezone.now()
        if settings.HIDE_NAIVE_AWARE_TYPE_ERROR and timezone.is_naive(after) and settings.USE_TZ:
            after = timezone.make_aware(after, timezone.utc)
        occ_replacer = OccurrenceReplacer(self.event_group.filter(original_start__gte = after))

        generator = self._occurrences_after_generator(after)

        trickies = list(self.event_group.filter(original_start__lte = after, start__gte=after).order_by('start'))

        while True:
            try:
                nxt = next(generator)
            except StopIteration:
                nxt = None

            while len(trickies) > 0 and (nxt is None or nxt.start > trickies[0].start):
                yield trickies.pop(0)
            
            if nxt is None:
                raise StopIteration

            yield occ_replacer.get_occurrence(nxt)

    def _occurrences_after_generator(self, after=None, tzinfo=timezone.utc):
        if after is None:
            after = timezone.now()
        rule = self.get_rrule_object()

        if rule is None:
            if self.end > after:
                yield self._create_occurrence(self.start, self.end)
            raise StopIteration

        else:
            date_iter = rule.xafter(after, inc=True)
            while True:
                start = next(date_iter)
                if self.rule.end_recurring_period and start > self.rule.end_recurring_period:
                    raise StopIteration
                end = start + self.duration
                if end > after:
                    yield self._create_occurrence(start, end)

class EventRelationManager(models.Manager):
    def get_events_for_object(self, content_object, distinction=None, queryset=Event.objects, inherit=True):
        ct = ContentType.objects.get_for_model(type(content_object))
        if distinction:
            dist_q = models.Q(eventrelation__distinction = distinction)
            cal_dist_q = models.Q(calendar__calendarrelation__distinction = distinction)
        else:
            dist_q = models.Q()
            cal_dist_q = models.Q()

        event_q = models.Q(
            dist_q,
            eventrelation__object_id=content_object.id,
            eventrelation__content_type=ct,
        )

        if inherit:
            inherit_q = models.Q(
                cal_dist_q,
                calendar__calendarrelation__object_id=content_object.id,
                calendar__calendarrelation__content_type=ct,
            )
        else:
            inherit_q = models.Q()

        # Event.obejcts
        return queryset.filter(inherit_q | event_q)

    def create_relation(self, event, content_object, distinction=None):
        er = EventRelation(
            event=event,
            distinction = distinction,
            content_object = content_object,
        )
        return er

    def save_relation(self, event, content_object, distinction=None):
        er = self.create_relation(event, content_object, distinction)
        er.save()
        return er


@python_2_unicode_compatible
class EventRelation(with_metaclass(models.base.ModelBase, *get_model_bases())):
    event = models.ForeignKey(Event)
    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField()
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    distinction = models.CharField(max_length=20, null=True)

    objects = EventRelationManager()

    def __str__(self):
        return '%i(%s)-%s' %( self.event.id, self.distinction, self.content_object )
