from django.db import models
from django.utils.module_loading import import_string
from scheduler.settings import settings

#The following three classes allow:
# * All Event Subclasses to share the EventManager (abstract classes pass on Managers!)
# * All Subclasses to be recognised by [SubClass].objects.get_for_object()
# * And all of them be returned in their corresponding type.

# Subclassing approach based on
# http://www.djangosnippets.org/snippets/1034/
class SubclassingQuerySet(models.QuerySet):
    def __getitem__(self, k):
        result = super(SubclassingQuerySet, self).__getitem__(k)
        if hasattr(result, 'as_leaf_class') :
            return result.as_leaf_class()
        else :
            return result

    def __iter__(self):
        for item in super(SubclassingQuerySet, self).__iter__():
            if hasattr(item, 'as_leaf_class'):
                yield item.as_leaf_class()
            else:
                yield item

#    def get(self, *args, **kwargs):
#        return super(SubclassingQuerySet, self).get(*args, **kwargs).as_leaf_class()

def get_model_bases():
    baseStrings = settings['SCHEDULER_BASE_CLASSES']
    if baseStrings is None:
        return [models.Model]
    else:
        return [import_string(x) for x in baseStrings]

class OccurrenceReplacer(object):

    def __init__(self, persisted_occurrences):
        lookup = [((occ.original_start, occ.original_end, occ.rule), occ) for occ in persisted_occurrences]
        self.lookup = dict(lookup)

    def get_occurrence(self, occ):
        return self.lookup.pop((occ.original_start, occ.original_end, occ.rule), occ)

    def has_occurrence(self, occ):
        try:
            return (occ.original_start, occ.original_end, occ.rule) in self.lookup
        except TypeError:
            if not self.lookup:
                return False
            else:
                raise TypeError('A problem during lookup of a persisted occurrence has occurred!')

    def get_additional_occurrences(self, start, end):
        return [occ for occ in list(self.lookup.values()) if (occ.start < end and occ.end >= start and not occ.cancelled)]


import operator
class NextOccurrenceReplacer(object):

    def __init__(self, persisted_occurrences):
        self.lookup = [((occ.original_start, occ.original_end, occ.rule), occ) for occ in sorted(persisted_occurrences, key=operator.attrgetter("start"), reverse=True)]

    def get_next_occurrences(self, occ):
        if self.lookup and (occ.original_start, occ.original_end, occ.rule) == self.lookup[-1][0]:
            return [self.lookup.pop()[1]]

        ret = []
        while self.lookup and self.lookup[-1][1].start <= occ.original_start:
            ret.append(self.lookup.pop()[1])
        return ret

    def is_next_occurrence(self, occ):
        if self.lookup and self.lookup[-1][0] == (occ.original_start, occ.original_end, occ.rule):
            return True
        return False

    def get_additional_occurrences(self, start, end):
        ret = []
        for tup_occ in self.lookup:
            occ = tup_occ[1]
            if occ.start < start:
                continue
            elif occ.start > end:
                break
            ret.apppend(occ)
        return ret

    def remaining_occurrences(self):
        return [tup_occ[1] for tup_occ in self.lookup]
