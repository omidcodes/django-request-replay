from django.urls import path

from .views import clear_queue, enqueue_command, get_queue


urlpatterns = [
    path("queue/", enqueue_command, name="enqueue_command"),
    path("queue/clear/", clear_queue, name="clear_queue"),
    path("queue/view/", get_queue, name="get_queue"),
]
