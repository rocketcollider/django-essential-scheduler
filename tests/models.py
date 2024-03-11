from scheduler.models import Event
from django.db import models

class FirstSub(Event):
    pass

class SecondSub(Event):
    pass

class ThirdSub(Event):
    pass

class TestSubEvent(ThirdSub):
    title = models.CharField(max_length=255)
