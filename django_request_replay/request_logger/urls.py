from django.urls import path
from .views import delete_request_history, DjangoRequestsHistoryViewSet

urlpatterns = [
    path("requests-history/", DjangoRequestsHistoryViewSet.as_view({'get': 'list'}), name="view_requests_history_list"),
    path("requests-history/clear/", delete_request_history, name="delete_request_history"),
]
