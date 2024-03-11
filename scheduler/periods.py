from __future__ import unicode_literals
from django.utils.six.moves.builtins import range
# -*- coding: utf-8 -*-

import datetime
from scheduler.settings import settings
from scheduler.models import Event
from django.db.models import Q
from django.utils import timezone
from django.utils.dates import WEEKDAYS, WEEKDAYS_ABBR
from django.utils.formats import date_format
from django.utils.encoding import python_2_unicode_compatible

weekday_names = []
weekday_abbrs = []


if settings.FIRST_DAY_OF_WEEK == 1:
    # The calendar week starts on Monday
    for i in range(7):
        weekday_names.append(WEEKDAYS[i])
        weekday_abbrs.append(WEEKDAYS_ABBR[i])
else:
    # The calendar week starts on Sunday, not Monday
    weekday_names.append(WEEKDAYS[6])
    weekday_abbrs.append(WEEKDAYS_ABBR[6])
    for i in range(6):
        weekday_names.append(WEEKDAYS[i])
        weekday_abbrs.append(WEEKDAYS_ABBR[i])



#for i in range(7-settings.FIRST_DAY_OF_WEEK):
#    weekday_names.append(WEEKDAYS[settings.FIRST_DAY_OF_WEEK+i])
#    weekday_abbrs.append(WEEKDAYS_ABBR[settings.FIRST_DAY_OF_WEEK+i])

#for i in range(settings.FIRST_DAY_OF_WEEK):
#    weekday_names.append(WEEKDAYS[i])
#    weekday_abbrs.append(WEEKDAYS_ABBR[i])


class Period(object):
    def __init__(self, events, start, end, persisted_occurrences=None, tzinfo = timezone.utc, occurrence_pool=None):
        self.utc_start = self._normalize_timezone_to_utc(start, tzinfo)
        self.utc_end = self._normalize_timezone_to_utc(end, tzinfo)
        self.events = events
        self.rules = [event.rule.pk for event in events if event.rule]
        self.tzinfo = self._get_tzinfo(tzinfo)
        self.occurrence_pool = occurrence_pool
        self._persisted_occurrences = persisted_occurrences

    def _normalize_timezone_to_utc(self, point_in_time, tzinfo):
        if not hasattr(point_in_time, 'tzinfo'):
            point_in_time=datetime.datetime.combine(point_in_time, datetime.time.min)
        if getattr(point_in_time, 'tzinfo', None) is not None:
            return point_in_time.astimezone(timezone.utc)
        if tzinfo is not None:
            return point_in_time.replace(tzinfo=tzinfo).astimezone(timezone.utc)
        if settings.USE_TZ:
            return point_in_time.replace(tzinfo=timezone.utc)
        else:
            if timezone.is_aware(point_in_time):
                return timezone.make_naive(point_in_time, timezone.utc)
            else:
                return point_in_time

    def __eq__(self, period):
        return type(period)==Period and \
            self.utc_start == period.utc_start and \
            self.utc_end == period.utc_end and \
            self.events == period.events

    def __ne__(self, period):
        return type(period) != Period or \
            self.utc_start != period.utc_start or \
            self.utc_end != period.utc_end or \
            self.events != periods.events

    def _get_tzinfo(self, tzinfo):
        return tzinfo if settings.USE_TZ else None

    def _get_sorted_occurrences(self):
        occurrences = []
        pool = getattr(self, "occurrence_pool", None)
        if pool is not None:
            for occurrence in pool:
                if occurrence.rule:
                    test =  occurrence.rule.pk in self.rules
                else:
                    test = occurrence in self.events
                if test and occurrence.start <= self.utc_end and occurrence.end >= self.utc_start:
                    occurrences.append(occurrence)
        else:
            # We only save DATETIME!
            if datetime.date in [type(self.start), type(self.end)]:
                start = datetime.datetime.combine(self.start, datetime.time.min.replace(tzinfo=timezone.utc))
                end = datetime.datetime.combine(self.end, datetime.time.min.replace(tzinfo=timezone.utc))
            else:
                start = self.start
                end = self.end
            
            sources = []
            for event in self.events:
                if event.group_source in sources:
                    continue
                else:
                    sources.append(event.group_source)
            for source in sources:
                event_occurrences = source.get_occurrences(start, end)
                occurrences += event_occurrences

        return sorted(occurrences)

    @property
    def occurrences(self):
        if hasattr(self, '_occurrences'):
            return self._occurrences
        self._occurrences = self._get_sorted_occurrences()
        return self._occurrences

    def get_persisted_occurrences(self):
        if not getattr(self, '_persisted_occurrences', None):
            events = Q(pk__in = self.events, rule=None) if None in self.rules else Q()
            groups = Q(rule__in=self.rules)
            self._persisted_occurrences = Event.objects.filter(groups | events)
        return self._persisted_occurrences

    @property
    def has_occurrences(self):
        return any(self.classify_occurrence(o) for o in self.occurrences)

    def classify_occurrence(self, occurrence):
        if occurrence.cancelled and not settings.SHOW_CANCELLED_OCCURRENCES:
            return
        if occurrence.start > self.end or occurrence.end < self.start:
            return None

        started = False
        ended = False
        if self.utc_start <= occurrence.start < self.utc_end:
            started = True
        if self.utc_start < occurrence.end <= self.utc_end:
            ended = True

        ret = {
            'occurrence':occurrence,
            'class':2,
            'cancelled':bool(getattr(occurrence, 'cancelled', False))
            }

        if started and ended:
            ret['class'] = 1
        elif startd:
            ret['class'] = 0
        elif ended:
            ret['class'] = 3

        return ret

    def get_occurrence_partials(self):
        occurrence_dicts = []
        for occ in self.occurrences:
            occurrence = self.classify_occurrence(occ)
            if occurrence:
                occurrence_dicts.append(occurrence)
        return occurrence_dicts

    def get_time_slot(self, start, end):
        if start < self.start or end > self.end:
            return None #Meaningful? "time-slot not in period, so I don't give you ANYTHING!" ?
        return Period(self.events, start, end)
        #suggest different behaviour:
        #    if start > end:
        #        return None
        #    if start < self.start:
        #        start = self.start
        #    if end > self.end:
        #        end = self.end

    @property
    def start(self):
        if not hasattr(self.utc_start, 'tzinfo'):
            return self.utc_start
        if self.tzinfo != None or type(self.utc_start) == datetime.date:
            return self.utc_start.astimezone(self.tzinfo)
        else:
            return self.utc_start.replace(tzinfo=None)

    @property
    def end(self):
        if not hasattr(self.utc_end, 'tzinfo'):
            return self.utc_end
        if self.tzinfo != None or type(self.utc_end) == datetime.date:
            return self.utc_end.astimezone(self.tzinfo)
        else:
            return self.utc_end.replace(tzinfo=None)

@python_2_unicode_compatible
class TimeRange(Period):

    def __init__(self, events, date=None, persisted_occurrences=None, tzinfo=timezone.utc, occurrence_pool=None):
        self.tzinfo=self._get_tzinfo(tzinfo)
        date = date or timezone.now().replace(tzinfo=self.tzinfo)
        start, end = self._get_range(date)
        super(TimeRange, self).__init__(events, start, end, persisted_occurrences, tzinfo, occurrence_pool)

    def __next__(self):
        return self.__class__(self.events, self.end, tzinfo=self.tzinfo)

    @property
    def next(self):
        return self.__next__()

    def __prev__(self):
        return self.__class__(self.events, self.time_range.rev().transpose(self.start), tzinfo = self.tzinfo)

    @property
    def prev(self):
        return self.__prev__()

    def get_periods(self, cls, tzinfo=None):
        tzinfo = tzinfo or self.tzinfo
        period = self.derive_sub_period(cls)
        while period.start < self.end:
            yield self.derive_sub_period(cls, period.start, tzinfo)
            period = next(period)

    def derive_sub_period(self, cls, start=None, tzinfo=None):
        tzinfo = tzinfo or self.tzinfo
        start = start or self.start
        return cls(self.events, start, self.get_persisted_occurrences(), tzinfo)

    def _get_range(self, start):
        if hasattr(self, "given_start"):
            naive_start = self.given_start(start)
        else:
            naive_start = start
        naive_end = self.time_range.transpose(naive_start)

        if self.tzinfo is None or type(naive_start) == type(naive_end) == datetime.date:
            start = naive_start
            end = naive_end
        else:
            local_start = naive_start.replace(tzinfo = self.tzinfo)
            local_end = naive_end.replace(tzinfo = self.tzinfo)
            start = local_start.astimezone(timezone.utc)
            end = local_end.astimezone(timezone.utc)

        return start, end

    def __str__(self):
        format = 'l, %s' %settings.DATE_FORMAT
        return "%s - %s" %(
                date_format(self.start, format),
                date_format(self.end, format)
            )

    def __getattr__(self, attr):
        if attr.startswith("get_") and attr[4:-1] in ['year', 'month', 'week', 'day']:
            cls = eval(attr[4:-1].capitalize())
            return self.get_periods(cls)
        elif attr.startswith('current_') and attr[8:] in ['year', 'month', 'week', 'day']:
            cls = eval(attr[8:].capitalize())
            return cls(self.events, self.start, self.get_persisted_occurrences())
        else:
            raise AttributeError("Can't find %s" %attr)

class TimeDelta(object):
    units = (
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "microsecond",
    )
    modulo=[
        0,      #years, will be ignored
        12,     #months
        31,     #days, requires more care!
        24,     #hours
        60,     #minuts
        60,     #seconds
        1000,   #microseconds
    ]

    def __init__(self, **kwargs):
        self.values = []
        for i, unit in enumerate(self.units):
            self.values.append(kwargs.get("%ss" %unit, 0))

    def rev(self):
        kwargs = dict([
            (unit+'s', -self.values[i])\
            for i, unit in enumerate(self.units)
        ])
        return TimeDelta(**kwargs)

    def transpose(self, other):
        """
            Expects a datetime object as argument,
            which will be transposed by a specified amount.
        """
        quarks = {}
        newMonth = False
        for i, unit in enumerate(self.units):
            if hasattr(other, unit) and self.values[i] !=0:
                quarks[unit] = (self.values[i] + getattr(other, unit))
                if i> 0 and quarks[unit] > self.modulo[i]:
                    quarks[unit] = quarks[unit] % self.modulo[i]
                    if self.units[i-1] in quarks:
                        quarks[self.units[i-1]] += 1
                    else:
                        quarks[self.units[i-1]] = getattr(other, self.units[i-1], 0) + 1
                    if unit == "day":
                        newMonth = True

        error = None
        for j in range(3):
            try:
                return other.replace(**quarks)
            except ValueError as e:
                if j > 2:
                    raise ValueError(e)
                quarks["day"] = quarks['day'] - 1 if 'day' in quarks else getattr(other, 'day', 0) - 1
                if not newMonth:
                    newMonth=True
                    quarks['month'] = quarks['month'] + 1 if 'month' in quarks else getattr(other, 'month', 0) + 1

    def __str__(self):
        return str(dict([(unit, self.values[i]) for i, unit in enumerate(self.units)]))

class Year(TimeRange):
    time_range = TimeDelta(years=1)

    def given_start(self, date):
        return datetime.date.min.replace(year=date.year)

class Month(TimeRange):
    time_range = TimeDelta(months=1)

    def given_start(self, date):
        return datetime.date.min.replace(year=date.year, month=date.month)

class Week(TimeRange):
    time_range = TimeDelta(days=7)

    def given_start(self, dt):
        assert(isinstance(dt, datetime.date))
        week = datetime.datetime.combine(dt.date(), datetime.time.min)
        sub_days = week.isoweekday()
        if settings.FIRST_DAY_OF_WEEK == 1:
            sub_days -= 1

        if 7 > sub_days > 0:
            week = week - datetime.timedelta(days=sub_days)

        return week

class Day(TimeRange):
    time_range = TimeDelta(days=1)

    def given_start(self, day):
        if self.tzinfo and timezone.is_aware(day):
            day = day.astimezone(self.tzinfo)

        ret = datetime.datetime.combine(day, datetime.time.min)
        return ret