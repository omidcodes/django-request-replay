from typing import Final

from rest_framework import status
from rest_framework.reverse import reverse

from .conf import settings
from .dataclasses import RequestResponseDataObject
from .helpers.dictionary import prettify_dict
from .helpers.request import (
    get_request_data_based_on_content_type,
    get_user_agent_key_from_request,
    get_ip_address_from_request,
)
from .models import DjangoRequestsHistoryModel

DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES: Final[list] = [reverse(url) for url in
                                                            settings.DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES]


class DjangoRequestsHistoryMiddleware:
    """
    Saves the history of all applied changes on DjangoRequestsHistoryModel.
    This middleware only works when `settings.DJANGO_REQUESTS_HISTORY_ENABLE` is set.

    Only saves:
        * The request's METHOD, PATH, and DATA in DjangoRequestsHistoryModel.
        * Request with successful response.
        * POST, PATCH, DELETE, PUT,... requests. To change this behaviour update
        `settings.DJANGO_REQUESTS_HISTORY_SAVABLE_REQUEST_METHODS` with more methods.

    Doesn't save:
        * requests that are in `settings.DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES`.
        * Request with unsuccessful status_code responses, e.g. 400, 500 ...
        * Requests with query parameter `?save=0`
        * Request with paths in `settings.DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES`
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # One-time configuration and initialization.
        self.request_response_info = RequestResponseDataObject()
        self.response = None
        self.request = None

    def __call__(self, request):
        # Code to be executed for each request before the view (and later middleware) are called.
        self.request = request
        self.__store_request_info()

        # Call view and get the response
        self.response = self.get_response(request)
        self.__store_response_info()

        # Code to be executed for each request/response after the view is called.
        if self.__is_request_savable():
            self.__save_config_to_db()

        return self.response

    def __store_request_info(self):
        """
        Stores request information in ConfigObject dataclass (self.request_response_info).
        We use this info to save request info in config DB after we find out that request is savable.

        ** Note: ** We should store this info before calling view, because after running `self.get_response(request)`
        (and calling view by Django), some request info are not accessible anymore.
        """
        assert self.request is not None

        content_type = self.request.META.get('CONTENT_TYPE', '')
        request_data_text, request_data_binary = get_request_data_based_on_content_type(self.request, content_type)

        requester_user_agent = get_user_agent_key_from_request(self.request)
        requester_ip_address = get_ip_address_from_request(self.request)
        requester_username = ""
        if getattr(self.request, "user", None) and self.request.user.is_authenticated:
            requester_username = self.request.user.username

        self.request_response_info = RequestResponseDataObject(
            request_method=self.request.method,
            request_path=self.request.path_info,
            request_data_text=request_data_text,
            request_data_binary=request_data_binary,
            request_content_type=content_type,
            requester_useragent=requester_user_agent,
            requester_ip=requester_ip_address,
            requester_username=requester_username,
        )

    def __store_response_info(self):
        assert self.request is not None
        if hasattr(self.response, "json"):
            dict_item = self.response.json()
            prettified_json = prettify_dict(dict_item)
            self.request_response_info.response_data_text = prettified_json
        elif hasattr(self.response, "data"):
            self.request_response_info.response_data_text = prettify_dict(self.response.data)
        elif hasattr(self.response, "text"):
            self.request_response_info.response_data_text = prettify_dict(self.response.text)

        self.request_response_info.response_status_code = self.response.status_code

    def __is_request_savable(self) -> bool:
        """ Checks multiple conditions and returns True if request must be saved """
        assert self.request is not None
        assert self.response is not None

        if self.request.method not in settings.DJANGO_REQUESTS_HISTORY_SAVABLE_REQUEST_METHODS:
            return False
        if not status.is_success(self.response.status_code):
            return False
        if not settings.DJANGO_REQUESTS_HISTORY_ENABLE:
            return False
        if self.request.GET.get('save') == '0':
            return False
        if self.request.path_info in DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES:
            return False
        return True

    def __save_config_to_db(self):
        """ Saves request parameters into the Config DB """
        assert self.request_response_info is not None
        DjangoRequestsHistoryModel.objects.create(
            request_method=self.request_response_info.request_method,
            request_path=self.request_response_info.request_path,
            request_data_text=self.request_response_info.request_data_text,
            request_data_binary=self.request_response_info.request_data_binary,
            request_content_type=self.request_response_info.request_content_type,
            requester_useragent=self.request_response_info.requester_useragent,
            requester_ip=self.request_response_info.requester_ip,
            requester_username=self.request_response_info.requester_username,
            response_code=self.request_response_info.response_status_code,
            response_data_text=self.request_response_info.response_data_text,
            label=None,
        )
