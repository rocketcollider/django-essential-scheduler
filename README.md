# Scheduler Django Plugin
This is the absolute bare essentials to implement calender-related features in django. There is no fluff, no frontend, just event-handling.

It was written in 2016. Django is currently on version 5.0, this was written for version 1.9.5. Don't use without significant touchups!

## History
This project started as a fork of llazzaro's [django-scheduler](https://github.com/llazzaro/django-scheduler). But quickly evolved into a complete rework, mainly changing the `Event`-model-class to allow subclassing for easy implementation into other projects, but still maintaning all collection-functions for calender-events.

The testing in this project grew extensively and was the reason for my first hire as test architect. Tests kept the code readable 8 years after it was finished.

## Usage
There is practically no immediate utility to this project. It requires another django project where models can be defined as subclasses of `Event`. To use it, add to `INSTALLED_APPS`:

```python
'scheduler',
```
(If you want to use automatic Occurrence discovery, make sure to add it AFTER any app that wants to use it!)

And in your model-definition, for example:

```python
from scheduler.models import Event, BaseEvent
from scheduler.models.occurrences import Occurrence

class MyEvents(Event):
    title = models.CharField()

class MyEvent_Occurrence(Occurrence):
    title = models.CharField() #has to have same fields as the Event-Subclass!

BaseEvent.occurrence_sublcasses[MyEvent.__name__] = MyEvent_Occurrence
```

This example defines a new `MiEvents` model with a new field `title`. `Occurence` is *not* a model and simply allows access to the `Event` model in non-database representations (such as recurrent events).