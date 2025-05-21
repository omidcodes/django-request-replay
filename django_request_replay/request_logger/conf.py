from django.conf import settings

settings.DJANGO_REQUESTS_HISTORY_ENABLE = bool(int(getattr(settings, "DJANGO_REQUESTS_HISTORY_ENABLE", True)))

settings.DJANGO_REQUESTS_HISTORY_SAVABLE_REQUEST_METHODS = getattr(
    settings,
    "DJANGO_REQUESTS_HISTORY_SAVABLE_REQUEST_METHODS",
    ('POST', 'PATCH', 'PUT', 'DELETE'),
)

settings.DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES = getattr(settings, "DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES",
                                                               tuple())

settings.DJANGO_REQUESTS_HISTORY_VIEW_FILTER = getattr(settings, "DJANGO_REQUESTS_HISTORY_VIEW_FILTER", {})
settings.DJANGO_REQUESTS_HISTORY_VIEW_ORDER_BY = getattr(settings, "DJANGO_REQUESTS_HISTORY_VIEW_ORDER_BY", "created")

settings.DJANGO_REQUESTS_HISTORY_VISIBLE_COLUMNS = getattr(settings, "DJANGO_REQUESTS_HISTORY_VISIBLE_COLUMNS",
                                                           "__all__")
