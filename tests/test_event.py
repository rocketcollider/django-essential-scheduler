import datetime

from django.utils import timezone

from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth.models import User

from scheduler.models import Event, Rule, Calendar, EventRelation
from scheduler.models.events import BaseEvent

from tests.models import *

class TestEvent(TestCase):

    def setUp(self):
        cal = Calendar(name="MyCal")
        cal.save()

    def __create_event(self, start, end, cal):
        return Event(**{
            'start':start,
            'end':end,
            'calendar':cal
        })

    def __create_recurring_event(self, start, end, rule, cal):
        return Event(**{

                'start': start,
                'end': end,
                'rule': rule,
                'calendar': cal
        })

    def test_edge_case_events(self):
        cal = Calendar(name="MyCal")
        cal.save()

        data_1 = {
            'start': datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
            'end': datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            'calendar': cal,
        }

        data_2 = {
            'start': datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            'end': datetime.datetime(2013, 1, 5, 12, 0, tzinfo=timezone.utc),
            'calendar': cal
        }
        event_one = Event(**data_1)
        event_two = Event(**data_2)
        event_one.save()
        event_two.save()

        occurrences_two = event_two.get_occurrences(datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                                                    datetime.datetime(2013, 1, 5, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(1, len(occurrences_two))

        occurrences_one = event_one.get_occurrences(datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                                                    datetime.datetime(2013, 1, 5, 12, 0, tzinfo=timezone.utc))

        self.assertEqual(0, len(occurrences_one))

    def test_recurring_event_get_occurrences(self):

        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period= datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()

        recurring_event = self.__create_recurring_event(

                    datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),

                    rule,
                    cal,
                    )
        recurring_event.save()

        occurrences = recurring_event.get_occurrences(start=datetime.datetime(2008, 1, 12, 0, 0, tzinfo=timezone.utc),
                                                      end=datetime.datetime(2008, 1, 20, 0, 0, tzinfo=timezone.utc))

        self.assertEqual(["%s to %s" % (o.start, o.end) for o in occurrences],
                          ['2008-01-12 08:00:00+00:00 to 2008-01-12 09:00:00+00:00',
                           '2008-01-19 08:00:00+00:00 to 2008-01-19 09:00:00+00:00'])


    def test_recurring_event_get_occurrences_2(self):
        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2013, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        rule2 = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2013, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule2.save()

        recurring_partly = self.__create_recurring_event(
                    datetime.datetime(2012, 12, 29, 11, 0, tzinfo=timezone.utc),
                    datetime.datetime(2012, 12, 29, 13, 0, tzinfo=timezone.utc),
                    rule,
                    cal,
                    )
        recurring_outside = self.__create_recurring_event(
                    datetime.datetime(2012, 12, 29, 13, 0, tzinfo=timezone.utc),
                    datetime.datetime(2012, 12, 29, 14, 0, tzinfo=timezone.utc),
                    rule2,
                    cal,
                    )

        recurring_outside.save()
        recurring_partly.save()

        test_window=[
            datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            datetime.datetime(2013, 1, 5, 12, 0, tzinfo=timezone.utc)
        ]

        recurrences_partly = recurring_partly.get_occurrences(*test_window)
        self.assertEqual(1, len(recurrences_partly))

        recurrences_outside = recurring_outside.get_occurrences(*test_window)
        self.assertEqual(0, len(recurrences_outside))

    def test_event_get_occurrences(self):

        cal = Calendar(name="MyCal")
        cal.save()
        event_outside = self.__create_event(
                datetime.datetime(2013, 1, 5, 7, 0, tzinfo=timezone.utc),
                datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                cal
        )
        event_partly = self.__create_event(
                datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2013, 1, 5, 10, 0, tzinfo=timezone.utc),
                cal
        )
        event_inside = self.__create_event(
                datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                datetime.datetime(2013, 1, 5, 11, 0, tzinfo=timezone.utc),

                cal
        )
        event_outside.save()
        event_partly.save()
        event_inside.save()
        test_window=[
            datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            datetime.datetime(2013, 1, 5, 12, 0, tzinfo=timezone.utc)
        ]

        occurrences_outside = event_outside.get_occurrences(*test_window)
        self.assertEqual(0, len(occurrences_outside))

        occurrences_partly = event_partly.get_occurrences(*test_window)
        self.assertEqual(1, len(occurrences_partly))

        occurrences_inside = event_inside.get_occurrences(*test_window)
        self.assertEqual(1, len(occurrences_inside))

    def test_recurring_event_get_occurrences_after(self):

        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        recurring_event= self.__create_recurring_event(
                    datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                    rule,
                    cal,
                    )

        recurring_event.save()
        occurrences = recurring_event.get_occurrences(start=datetime.datetime(2008, 1, 5, tzinfo=timezone.utc),
            end = datetime.datetime(2008, 1, 6, tzinfo=timezone.utc))
        occurrence = occurrences[0]
        occurrence2 = next(recurring_event.occurrences_after(datetime.datetime(2008, 1, 5, tzinfo=timezone.utc)))
        self.assertEqual(occurrence, occurrence2)

    def test_recurring_event_get_occurrences_after_with_moved_occ(self):


        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()
        recurring_event= self.__create_recurring_event(

                    datetime.datetime(2008, 1, 1, 2, 0, tzinfo=timezone.utc),
                    datetime.datetime(2008, 1, 1, 3, 0, tzinfo=timezone.utc),

                    rule,
                    cal,
                    )

        recurring_event.save()
        occurrence = recurring_event.get_occurrence(datetime.datetime(2008, 1, 8, 2, 0, tzinfo=timezone.utc), True)
        occurrence.move(
          datetime.datetime(2008, 1, 15, 2, 0, tzinfo=timezone.utc),
          datetime.datetime(2008, 1, 15, 3, 0, tzinfo=timezone.utc))
        occurrence2 = recurring_event.get_occurrence(
          datetime.datetime(2008, 1, 14, 8, 0, tzinfo=timezone.utc))
        self.assertEqual(occurrence, occurrence2)
        self.assertEqual(datetime.datetime(2008, 1, 15, 2, 0, tzinfo=timezone.utc), occurrence2.start)

    def test_recurring_event_get_occurrence(self):

        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()

        event = self.__create_recurring_event(
                datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                rule,
                cal,
            )
        event.save()

        occurrence = event.get_occurrence(datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc))
        occurrence.save()
        self.assertEqual(occurrence.start, datetime.datetime(2008, 1, 5, 8, tzinfo=timezone.utc))
        occurrence = event.get_occurrence(datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc))
        self.assertTrue(occurrence.pk is not None)

    @override_settings(HIDE_NAIVE_AWARE_TYPE_ERROR=True)
    def test_prevent_TypeError_when_comparing_naive_w_aware_dates(self):
        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()

        event = self.__create_recurring_event(
                datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                rule,
                cal,
            )

        naive_date = datetime.datetime(2008, 1, 20, 0, 0)
        self.assertIsNone(event.get_occurrence(naive_date, True))

    @override_settings(USE_TZ=False)
    def test_prevent_TypeError_when_comparing_dates_when_tz_off(self):
        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0))
        rule.save()

        event = self.__create_recurring_event(
                    datetime.datetime(2008, 1, 5, 8, 0),
                    datetime.datetime(2008, 1, 5, 9, 0),
                    rule,
                    cal,
                    )
        naive_date = datetime.datetime(2008, 1, 20, 0, 0)
        self.assertIsNone(event.get_occurrence(naive_date, True))

    def test_event_get_ocurrence(self):

        cal = Calendar(name='MyCal')
        cal.save()
        start = timezone.now() + datetime.timedelta(days=1)
        event = self.__create_event(
                            start,
                            start + datetime.timedelta(hours=1),
                            cal)
        event.save()
        occurrence = event.get_occurrence(start)
        self.assertEqual(occurrence.start, start)

    def test_occurences_after_with_no_params(self):

        cal = Calendar(name='MyCal')
        cal.save()
        start = timezone.now() + datetime.timedelta(days=1)
        event = self.__create_event(
                            start,
                            start + datetime.timedelta(hours=1),
                            cal)
        event.save()
        occurrences = list(event.occurrences_after())
        self.assertEqual(len(occurrences), 1)
        self.assertEqual(occurrences[0].start, start)
        self.assertEqual(occurrences[0].end, start + datetime.timedelta(hours=1))

    def test_occurences_with_recurrent_event_end_recurring_period_edge_case(self):

        start = timezone.now() + datetime.timedelta(days=1)
        cal = Calendar(name='MyCal')
        cal.save()
        rule = Rule(frequency="DAILY", end_recurring_period=start + datetime.timedelta(days=10))
        rule.save()
        event = self.__create_recurring_event(
                            start,
                            start + datetime.timedelta(hours=1),
                            rule,
                            cal)
        event.save()
        occurrences = list(event.occurrences_after())
        self.assertEqual(len(occurrences), 11)

    def test_get_for_object(self):
        user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
        event_relations = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(event_relations), 0)

        rule = Rule(frequency="DAILY")
        rule.save()
        cal = Calendar(name='MyCal')
        cal.save()
        event = self.__create_event(
                datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                cal
        )
        event.save()
        events = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(events), 0)
        EventRelation.objects.save_relation(event, user, 'owner')

        events = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(events), 1)
        self.assertEqual(event, events[0])

    def test_event_by_slug(self):
        cal = Calendar(name='MyCal')
        cal.save()
        start = timezone.now() + datetime.timedelta(days=1)
        event = self.__create_event(
                            start,
                            start + datetime.timedelta(hours=1),
                            cal)
        event.save()
        occurrence = Event.objects.get(slug="1")
        self.assertEqual(occurrence.start, start)

    def test_occurrence_by_slug(self):
        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()

        event = self.__create_recurring_event(
                datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                rule,
                cal,
            )
        event.save()

        occurrence = Event.objects.get(slug="%i-%s"%(event.pk, datetime.datetime(2008, 1, 12, 8, 0, tzinfo=timezone.utc).strftime('%Y-%m-%d-%H-%M%z')))
        self.assertEqual(occurrence.start, datetime.datetime(2008, 1, 12, 8, tzinfo=timezone.utc))

        occurrence2 = Event.objects.get(slug="%i-%s"%(event.pk, datetime.datetime(2008, 1, 13, 8, 0, tzinfo=timezone.utc).strftime('%Y-%m-%d-%H-%M%z')))
        self.assertEqual(occurrence2.start, datetime.datetime(2008, 1, 19, 8, tzinfo=timezone.utc))

        filtered1 = Event.objects.filter(slug="%i-%s"%(event.pk, datetime.datetime(2008, 1, 12, 8, 0, tzinfo=timezone.utc).strftime('%Y-%m-%d-%H-%M%z')))
        #can we avoid inifinite recursion?
        filtered1._fetch_all()
        self.assertEqual(filtered1[0].start, datetime.datetime(2008, 1, 12, 8, tzinfo=timezone.utc))

        filtered2 = Event.objects.filter(slug="%i-%s"%(event.pk, datetime.datetime(2008, 1, 13, 8, 0, tzinfo=timezone.utc).strftime('%Y-%m-%d-%H-%M%z')))
        self.assertEqual(filtered2[0].start, datetime.datetime(2008, 1, 19, 8, tzinfo=timezone.utc))

    def test_simple_event_slug_value(self):
        cal = Calendar(name="MyCal")
        cal.save()
        event = self.__create_event(
                datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                cal,
            )
        self.assertEqual(event.slug, None)
        event.save()
        self.assertEqual(event.pk, 1)
        self.assertEqual(event.slug, '1-2008-01-05-08-00+0000')

    def test_recurring_event_slug_value(self):
        cal = Calendar(name="MyCal")
        cal.save()
        rule = Rule(frequency="WEEKLY", end_recurring_period=datetime.datetime(2008, 5, 5, 0, 0, tzinfo=timezone.utc))
        rule.save()

        event = self.__create_recurring_event(
                datetime.datetime(2008, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2008, 1, 5, 9, 0, tzinfo=timezone.utc),
                rule,
                cal,
            )
        self.assertEqual(event.slug, None)
        event.save()
        self.assertEqual(event.slug, '1-2008-01-05-08-00+0000')

class TestEventInheritance(TestEvent):

    def __create_event(self, title, start, end, cal):
        return TestSubEvent(**{
                'title': title,
                'start': start,
                'end': end,
                'calendar': cal
        })

    def __create_recurring_event(self, title, start, end, rule, cal):
        return TestSubEvent(**{
                'title': title,
                'start': start,
                'end': end,
                'rule': rule,
                'calendar': cal
        })

    def test_event_inheritence(self):
        cal = Calendar(name="MyCal")
        cal.save()
        event = self.__create_event(
            "Heeello!",
            datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
            datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            cal
        )
        event.save()
        occ = event.get_occurrences(
            datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
            datetime.datetime(2014, 1, 5, 8, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(1, len(occ))

    def test_get_for_object(self):
        user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
        event_relations = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(event_relations), 0)

        rule = Rule(frequency="DAILY")
        rule.save()
        cal = Calendar(name='MyCal')
        cal.save()
        event = self.__create_event(
                'event test',
                datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
                datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
                cal
        )
        event.save()
        events = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(events), 0)
        EventRelation.objects.save_relation(event, user, 'owner')

        self.assertEqual(len(list(event.eventrelation_set.all())), 1)

        events = list(Event.objects.get_for_object(user, 'owner'))
        self.assertEqual(len(events), 1)
        self.assertEqual(type(events[0]), TestSubEvent)
        self.assertEqual(event, events[0])

    def test_subclassing_queryset(self):
        cal = Calendar(name="MyCal")
        cal.save()
        event = self.__create_event(
            "Heeello!",
            datetime.datetime(2013, 1, 5, 8, 0, tzinfo=timezone.utc),
            datetime.datetime(2013, 1, 5, 9, 0, tzinfo=timezone.utc),
            cal
        )
        event.save()
        ev = Event.objects.filter(pk=1)[0]
        self.assertTrue(isinstance(ev, TestSubEvent))

        newev = Event.objects.get(pk=1)
        testev = newev.as_leaf_class()
        self.assertEqual(testev, ev)
