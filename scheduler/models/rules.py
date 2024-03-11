
from dateutil import rrule
from django.db import models
from django.utils.six import with_metaclass
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six.moves.builtins import str

from scheduler.models.utils import get_model_bases

freqs = (("YEARLY", "Yearly"),
    ("MONTHLY", "Monthly"),
    ("WEEKLY", "Weekly"),
    ("DAILY", "Daily"),
    ("HOURLY", "Hourly"),
    ("MINUTELY", "Minutely"),
    ("SECONDLY", "Secondly"))

@python_2_unicode_compatible
class Rule(with_metaclass(models.base.ModelBase, *get_model_bases())):
    name=models.CharField(max_length=32)
    description = models.TextField()
    frequency = models.CharField(choices=freqs, max_length=10)
    start_recurring_period = models.DateTimeField(null=True, blank=True)
    end_recurring_period = models.DateTimeField(null=True, blank=True)
    params = models.TextField(null=True, blank=True)

    def rrule_frequency(self):
        compatibility_dict={
            'YEARLY': rrule.YEARLY,
            'MONTHLY': rrule.MONTHLY,
            'WEEKLY': rrule.WEEKLY,
            'DAILY': rrule.DAILY,
            'HOURLY': rrule.HOURLY,

        }
        return compatibility_dict[self.frequency]

    def create(self, *args, **kwargs):
        return super(Rule, self).create(self, *args, **kwargs)

    def get_params(self):
        if self.params is None:
            return {}
        params = self.params.split(';')
        param_dict = []
        for param in params:
            param = param.split(':')
            if len(param) == 2:
                param = (str(param[0]), [int(p) for p in param[1].split(',')])
                if len(param[1]) == 1:
                    param = (param[0], param[1][0])
                param_dict.append(param)
        return dict(param_dict)

    def __str__(self):
        return "Rule %s, params: %s" %(self.name, self.params)