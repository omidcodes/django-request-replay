from dataclasses import dataclass


@dataclass
class RequestResponseDataObject:
    """ DataClass which holds object data relating to each request and its response """

    request_method: str = ""
    request_path: str = ""
    request_data_text: str = ""
    request_data_binary: bytes = bytes()
    request_content_type: str = ""
    requester_useragent: str = ""
    requester_username: str = ""
    requester_ip: str = ""
    response_status_code: int = 0
    response_data_text: str = ""
