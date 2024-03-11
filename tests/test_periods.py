from django.utils.six.moves.builtins import zip
from django.utils.six.moves.builtins import range
import datetime

from django.test import TestCase
from django.conf import settings
from django.utils import timezone

from scheduler.models import Event, Rule, Calendar
from scheduler.periods import Period, Month, Day, Year, Week


class NewYork(datetime.tzinfo):

    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5, days=0)

    def tzname(self, dt):
        return "New York"

    def dst(self, dt):
        return datetime.timedelta(0)

    def localize(self, dt):
        return dt.replace(tzinfo=self)

class TestPeriod(TestCase):

    def setUp(self):
        rule = Rule(frequency = "WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        cal = Calendar(name="MyCal")
        cal.save()
        data = {
                'start': datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                'end': datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                'rule': rule,
                'calendar': cal
        }
        data2 = {
                'start': datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                'end': datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                'calendar': cal
        }
        recurring_event = Event(**data)
        recurring_event.save()
        singular_event = Event(**data2)
        singular_event.save()
        self.period = Period(events=Event.objects.source_events(),
                            start = datetime.datetime(2008, 1, 4, 7, 0, tzinfo=timezone.utc),
                            end = datetime.datetime(2008, 1, 21, 7, 0, tzinfo=timezone.utc))

    def test_get_occurrences(self):
        occurrence_list = self.period.occurrences
        self.assertEqual(["%s to %s" %(o.start, o.end) for o in occurrence_list],
                ['2008-01-05 08:00:00+00:00 to 2008-01-05 09:00:00+00:00',
                    '2008-01-12 08:00:00+00:00 to 2008-01-12 09:00:00+00:00',
                    '2008-01-19 08:00:00+00:00 to 2008-01-19 09:00:00+00:00'])

    def test_get_occurrence_partials(self):
        occurrence_dicts = self.period.get_occurrence_partials()
        self.assertEqual(
            [(occ_dict["class"],
            occ_dict["occurrence"].start,
            occ_dict["occurrence"].end)
            for occ_dict in occurrence_dicts],
            [
                (1,
                 datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc)),
                (1,
                 datetime.datetime(2008, 1, 12, 8, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 12, 9, 0, tzinfo=timezone.utc)),
                (1,
                 datetime.datetime(2008, 1, 19, 8, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 19, 9, 0, tzinfo=timezone.utc))
            ])

    def test_has_occurrence(self):
        self.assert_( self.period.has_occurrences )
        slot = self.period.get_time_slot( datetime.datetime(2008, 1, 4, 7, 0, tzinfo=timezone.utc),
                                          datetime.datetime(2008, 1, 4, 7, 12, tzinfo=timezone.utc) )
        self.failIf( slot.has_occurrences )

    def test_occurrence_pool_w_wrong_group(self):
        occ = self.period.events[0].get_occurrences(
            start = datetime.datetime(2008, 1, 4, 7, 0, tzinfo=timezone.utc),
            end = datetime.datetime(2008, 1, 21, 7, 0, tzinfo=timezone.utc) 
        )
        occ[0].rule = Rule(frequency="YEARLY")
        occ.append(self.period.events[1].get_occurrence(datetime.datetime(2008, 1, 4, 7, 0, tzinfo=timezone.utc)))
        self.period.occurrence_pool = occ
        occurrences = self.period.occurrences
        self.assertEqual(len(occurrences), 3)

    def test_get_persisted_occurrences(self):
        self.period.events[0].get_occurrences(
            start = datetime.datetime(2008, 1, 4, 7, 0, tzinfo=timezone.utc),
            end = datetime.datetime(2008, 1, 21, 7, 0, tzinfo=timezone.utc) 
        )[0].move(datetime.datetime(2008, 1, 19, 8, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 19, 9, 0, tzinfo=timezone.utc))
        persisted = self.period.get_persisted_occurrences()
        self.assertEqual(len(persisted), 2)
        self.assertTrue(self.period.events[1] in persisted)

class TestYear(TestCase):

    def setUp(self):
        self.year = Year(events=[], date=datetime.datetime(2008, 4, 1, tzinfo=timezone.utc))

    def test_get_months(self):
        months = self.year.get_months
        self.assertEqual([month.start for month in months],
            [datetime.datetime(2008, i, 1, tzinfo=timezone.utc) for i in range(1,13)])

class TestMonth(TestCase):

    def setUp(self):
        rule = Rule(frequency = "WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        cal = Calendar(name="MyCal")
        cal.save()
        data = {
                'start': datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                'end': datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                'rule': rule,
                'calendar': cal
               }
        recurring_event = Event(**data)
        recurring_event.save()
        self.month = Month(events=Event.objects.source_events(),
                           date=datetime.datetime(2008, 2, 7, 9, 0, tzinfo=timezone.utc))

    def pest_get_weeks(self):
        weeks = self.month.get_weeks()
        actuals = [(week.start, week.end) for week in weeks]

        if settings.FIRST_DAY_OF_WEEK == 0:
            expecteds = [
                (datetime.datetime(2008, 1, 27, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 3, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 3, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 10, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 10, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 17, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 17, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 24, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 24, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 3, 2, 0, 0, tzinfo=timezone.utc))
            ]
        else:
            expecteds = [
                (datetime.datetime(2008, 1, 28, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 4, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 4, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 11, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 11, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 18, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 18, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 25, 0, 0, tzinfo=timezone.utc)),
                (datetime.datetime(2008, 2, 25, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 3, 3, 0, 0, tzinfo=timezone.utc))
            ]

        for actual, expected in zip(actuals, expecteds):
            self.assertEqual(actual, expected)

    def test_get_days(self):
        weeks = self.month.get_weeks
        week = list(weeks)[0]
        days = week.get_days
        actuals = [(len(day.occurrences), day.start,day.end) for day in days]

        if settings.FIRST_DAY_OF_WEEK == 0:
            expecteds = [
                (
                    0,
                    datetime.datetime(2008, 1, 27, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 28, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    0,
                    datetime.datetime(2008, 1, 28, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 29, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    0,
                    datetime.datetime(2008, 1, 29, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 30, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    0,
                    datetime.datetime(2008, 1, 30, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 31, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    0,
                    datetime.datetime(2008, 1, 31, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 2, 1, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    0,
                    datetime.datetime(2008, 2, 1, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 2, 2, 0, 0, tzinfo=timezone.utc)
                ),
                (
                    1,
                    datetime.datetime(2008, 2, 2, 0, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 2, 3, 0, 0, tzinfo=timezone.utc)
                ),
            ]

        else:
            expecteds = [
                (0, datetime.datetime(2008, 1, 28, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 29, 0, 0, tzinfo=timezone.utc)),
                (0, datetime.datetime(2008, 1, 29, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 30, 0, 0, tzinfo=timezone.utc)),
                (0, datetime.datetime(2008, 1, 30, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 1, 31, 0, 0, tzinfo=timezone.utc)),
                (0, datetime.datetime(2008, 1, 31, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 1, 0, 0, tzinfo=timezone.utc)),
                (0, datetime.datetime(2008, 2, 1, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 2, 0, 0, tzinfo=timezone.utc)),
                (1, datetime.datetime(2008, 2, 2, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 3, 0, 0, tzinfo=timezone.utc)),
                (0, datetime.datetime(2008, 2, 3, 0, 0, tzinfo=timezone.utc),
                 datetime.datetime(2008, 2, 4, 0, 0, tzinfo=timezone.utc))
            ]

        for actual, expected in zip(actuals, expecteds):
            self.assertEqual(actual, expected)


    def test_month_convenience_functions(self):
        self.assertEqual( self.month.prev.start, datetime.datetime(2008, 1, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.month.next.start, datetime.datetime(2008, 3, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.month.current_year.start, datetime.datetime(2008, 1, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.month.current_year.prev.start, datetime.datetime(2007, 1, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.month.current_year.next.start, datetime.datetime(2009, 1, 1, 0, 0, tzinfo=timezone.utc))

class TestDay(TestCase):
    def setUp(self):
        self.day = Day(events=Event.objects.all(),
                           date=datetime.datetime(2008, 2, 7, 9, 0, tzinfo=timezone.utc))

    def test_day_setup(self):
        self.assertEqual( self.day.start, datetime.datetime(2008, 2, 7, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.day.end, datetime.datetime(2008, 2, 8, 0, 0, tzinfo=timezone.utc))

    def test_day_convenience_functions(self):
        self.assertEqual( self.day.prev.start, datetime.datetime(2008, 2, 6, 0, 0, tzinfo=timezone.utc))
        self.assertEqual( self.day.next.start, datetime.datetime(2008, 2, 8, 0, 0, tzinfo=timezone.utc))

    def test_time_slot(self):
        slot_start = datetime.datetime(2008, 2, 7, 13, 30, tzinfo=timezone.utc)
        slot_end = datetime.datetime(2008, 2, 7, 15, 0, tzinfo=timezone.utc)
        period = self.day.get_time_slot( slot_start, slot_end )
        self.assertEqual( period.start, slot_start )
        self.assertEqual( period.end, slot_end )

    def test_get_day_range(self):
        # This test exercises the case where a Day object is initiatized with
        # no date, which causes the Day constructor to call timezone.now(),
        # which always uses UTC.  This can cause a problem if the desired TZ
        # is not UTC, because the _get_day_range method typecasts the
        # tz-aware datetime to a naive datetime.

        # To simulate this case, we will create a NY tz date, localize that
        # date to UTC, then create a Day object with the UTC date and NY TZ

        NY = NewYork()
        user_wall_time = datetime.datetime(2015, 11, 4, 21, 30, tzinfo=NY)
        timezone_now = user_wall_time.astimezone(timezone.utc)

        #THIS IS TO SIMULATE timezone.now() WITH FIXED DATE!!!!
        test_day = Day(
            events=Event.objects.all(),
            date=timezone_now,
            tzinfo=NY)

        expected_start = datetime.datetime(2015, 11, 4, 5, 00, tzinfo=timezone.utc)
        expected_end = datetime.datetime(2015, 11, 5, 5, 00, tzinfo=timezone.utc)

        self.assertEqual( test_day.start, expected_start)
        self.assertEqual( test_day.end, expected_end)

class TestTzInfoPersistence(TestCase):
    def setUp(self):
        self.timezone = NewYork()
        self.day = Day(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone
        )

        self.week = Week(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone,
        )

        self.month = Month(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone,
        )

        self.year = Year(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone,
        )

    def test_persistence(self):
        self.assertEqual(self.day.tzinfo, self.timezone)
        self.assertEqual(self.week.tzinfo, self.timezone)
        self.assertEqual(self.month.tzinfo, self.timezone)
        self.assertEqual(self.year.tzinfo, self.timezone)

class TestAwareDay(TestCase):
    def setUp(self):
        self.timezone = NewYork()

        start = self.timezone.localize(datetime.datetime(2008, 2, 7, 0, 20))
        end = self.timezone.localize(datetime.datetime(2008, 2, 7, 0, 21))
        self.event = Event(
            start=start,
            end=end,
        )
        self.event.save()

        self.day = Day(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2008, 2, 7, 9, 0)),
            tzinfo=self.timezone,
        )

    def test_day_range(self):
        start = datetime.datetime(2008, 2, 7, 5, 0, tzinfo=timezone.utc)
        end = datetime.datetime(2008, 2, 8, 5, 0, tzinfo=timezone.utc)

        self.assertEqual(start, self.day.start)
        self.assertEqual(end, self.day.end)

    def test_occurence(self):
        self.assertTrue(self.event in self.day.occurrences)


class TestAwareWeek(TestCase):
    def setUp(self):
        self.timezone = NewYork()
        self.week = Week(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone,
        )

    def test_week_range(self):
        start = self.timezone.localize(datetime.datetime(2013, 12, 15, 0, 0))
        end = self.timezone.localize(datetime.datetime(2013, 12, 22, 0, 0))

        self.assertEqual(self.week.tzinfo, self.timezone)
        self.assertEqual(start, self.week.start)
        self.assertEqual(end, self.week.end)


class TestAwareMonth(TestCase):
    def setUp(self):
        self.timezone = NewYork()
        self.month = Month(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 11, 17, 9, 0)),
            tzinfo=self.timezone,
        )

    def test_month_range(self):
        start = self.timezone.localize(datetime.datetime(2013, 11, 1, 0, 0))
        end = self.timezone.localize(datetime.datetime(2013, 12, 1, 0, 0))

        self.assertEqual(self.month.tzinfo, self.timezone)
        self.assertEqual(start, self.month.start)
        self.assertEqual(end, self.month.end)


class TestAwareYear(TestCase):
    def setUp(self):
        self.timezone = NewYork()
        self.year = Year(
            events=Event.objects.all(),
            date=self.timezone.localize(datetime.datetime(2013, 12, 17, 9, 0)),
            tzinfo=self.timezone,
        )

    def test_year_range(self):
        start = self.timezone.localize(datetime.datetime(2013, 1, 1, 0, 0))
        end = self.timezone.localize(datetime.datetime(2014, 1, 1, 0, 0))

        self.assertEqual(self.year.tzinfo, self.timezone)
        self.assertEqual(start, self.year.start)
        self.assertEqual(end, self.year.end)

class TestOccurrencePool(TestCase):

    def setUp(self):
        rule = Rule(frequency = "WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        cal = Calendar(name="MyCal")
        cal.save()
        data = {
                'start': datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                'end': datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                'rule': rule,
                'calendar': cal
               }
        self.recurring_event = Event(**data)
        self.recurring_event.save()

    def testPeriodFromPool(self):
        """
            Test that period initiated with occurrence_pool returns the same occurrences as "straigh" period
            in a corner case whereby a period's start date is equal to the occurrence's end date
        """
        start = datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc)
        end = datetime.datetime(2008, 1, 5, 10, 0, tzinfo=timezone.utc)
        parent_period = Period(Event.objects.all(), start, end)
        period = Period(parent_period.events, start, end, parent_period.get_persisted_occurrences(), occurrence_pool=parent_period.occurrences)
        self.assertEqual(parent_period.occurrences, period.occurrences)