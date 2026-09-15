from django.conf import settings as default_settings

class Settings(object):

    def __init__(self, **kwargs):
        self.settings = kwargs

    def __getattr__(self, attr):
        if attr == "debug":
            print("CALLED IT!")
            print(hasattr(default_settings, 'debug'))
        if attr == 'settings':
            return super(Settings, self).__getattr__('settings')
        return self[attr]

    def __getitem__(self, key):
        return getattr(default_settings, key, self.settings.get(key, None))

settings = Settings(
    SCHEDULER_BASE_CLASSES = None,
    FIRST_DAY_OF_WEEK = 1,
    HIDE_NAIVE_AWARE_TYPE_ERROR = False,
    USE_TZ = True,
)