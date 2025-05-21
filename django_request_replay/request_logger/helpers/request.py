from abc import ABC, abstractmethod
from typing import Final

from .dictionary import prettify_dict


def get_user_agent_key_from_request(request) -> str:
    """
    gets user agent from request.

    if axes is being used it returns a cleaner text, e.g.:
        "android, Chrome 129.0"
    else it returns something messy:
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)
        Chrome/128.0.0.0 Safari/537.36"
    :param request:
    :return:
    """
    requester_http_user_agent: Final[str] = request.META.get('HTTP_USER_AGENT', '')
    if not hasattr(request, 'user_agent'):
        return requester_http_user_agent

    user_os_family = request.user_agent.os.family  # e.g. android, ios
    user_browser_family = request.user_agent.browser.family  # e.g. chrome, firefox
    user_browser_version = request.user_agent.browser.version_string

    axes_user_agent: str = f"{user_os_family}, {user_browser_family} {user_browser_version}"
    return axes_user_agent or requester_http_user_agent


def get_ip_address_from_request(request) -> str:
    meta_http_x_forwarded_for: Final[str] = request.META.get('HTTP_X_FORWARDED_FOR', '')
    meta_remote_addr: Final[str] = request.META.get('REMOTE_ADDR', '')
    requester_ip_address = meta_http_x_forwarded_for or meta_remote_addr
    return requester_ip_address


class _ContentTypeHandler(ABC):
    def __init__(self, next_handler=None):
        self.next_handler = next_handler

    @abstractmethod
    def handle(self, request, content_type):
        pass

    def process_next(self, request, content_type):
        if self.next_handler:
            return self.next_handler.handle(request, content_type)
        return self.handle_default(request)

    def handle_default(self, request):
        try:
            request_data_text = request.body.decode('utf-8')
            request_data_binary = request.body
        except UnicodeDecodeError:
            request_data_text = ''
            request_data_binary = request.body
        return request_data_text, request_data_binary


class _JsonContentHandler(_ContentTypeHandler):
    def handle(self, request, content_type):
        if content_type == 'application/json':
            try:
                decoded_request_data = request.body.decode('utf-8')
                request_data_text = prettify_dict(decoded_request_data)
                request_data_binary = request_data_text.encode()
                return request_data_text, request_data_binary
            except UnicodeDecodeError:
                request_data_text = request.body.decode(errors='ignore')
                request_data_binary = request.body
                return request_data_text, request_data_binary
        return self.process_next(request, content_type)


class _FormUrlencodedContentHandler(_ContentTypeHandler):
    def handle(self, request, content_type):
        if content_type == 'application/x-www-form-urlencoded':
            request_data_text = prettify_dict(request.POST.dict())
            request_data_binary = None
            return request_data_text, request_data_binary
        return self.process_next(request, content_type)


class _MultipartFormDataContentHandler(_ContentTypeHandler):
    def handle(self, request, content_type):
        if content_type.startswith('multipart/form-data'):
            request_data_dict = request.POST.dict()  # Non-file form data
            files_data = {}
            for file_key, file_obj in request.FILES.items():
                files_data[file_key] = {
                    'filename': file_obj.name,
                    'size': file_obj.size,
                    'content_type': file_obj.content_type,
                }
            request_data_dict['uploaded_files'] = files_data
            request_data_binary = request.body  # Store raw binary data
            request_data_text = prettify_dict(request_data_dict)
            return request_data_text, request_data_binary
        return self.process_next(request, content_type)


def get_request_data_based_on_content_type(request, content_type):
    # Chain the handlers
    handler_chain = _JsonContentHandler(
        _FormUrlencodedContentHandler(
            _MultipartFormDataContentHandler()
        )
    )

    # Process the request
    return handler_chain.handle(request, content_type)
