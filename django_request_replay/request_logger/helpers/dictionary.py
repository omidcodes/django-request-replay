import json
from typing import Union, Any


def convert_to_serializable_dict(data: Union[dict, Any]) -> Union[dict, str]:
    """
    Convert a given input to a dictionary if possible.
    Returns an empty dictionary if conversion is not possible.
    """

    if not isinstance(data, dict) and not hasattr(data, "items"):
        data_as_dict: dict = {}

        try:
            data_as_dict = json.loads(data)
        except Exception:  # nosec # pylint: disable=broad-except
            return str(data)
        return data_as_dict

    new_data: dict = {}
    for key, value in data.items():
        new_data[key] = str(value)

    return new_data


def prettify_json(data: Union[dict, str]) -> str:
    """
    Convert a dictionary to a JSON-formatted string.
    """
    try:
        return json.dumps(data, indent=4, sort_keys=True)
    except Exception:  # nosec # pylint: disable=broad-except
        return str(data)


def prettify_dict(possible_dict: Union[dict, Any]) -> str:
    """
    Tries to prettify a given input as a JSON-formatted string.
    Falls back to a simple string representation if not possible.
    """
    if possible_dict is None:
        return ""

    converted_dict = convert_to_serializable_dict(possible_dict)

    return prettify_json(converted_dict)
