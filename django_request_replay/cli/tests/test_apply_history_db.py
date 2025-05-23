import unittest
import json
from unittest.mock import patch, MagicMock
# from django_request_replay.cli.apply_history_db import RequestReplayer, Row, ColumnNames
from ..apply_history_db import RequestReplayer, Row, ColumnNames

class TestRequestReplayer(unittest.TestCase):

    def setUp(self):
        self.sample_row_data = {
            "id": 1,
            "label": "test",
            "request_method": "POST",
            "request_path": "/api/test",
            "request_data_binary": json.dumps({"name": "test"}).encode(),
            "response_code": 200
        }
        self.row = Row(
            keys=list(ColumnNames().table_displaying_names),
            data=[
                self.sample_row_data["id"],
                self.sample_row_data["label"],
                self.sample_row_data["request_method"],
                self.sample_row_data["request_path"],
                self.sample_row_data["request_data_binary"],
                self.sample_row_data["response_code"]
            ]
        )

    def test_parse_request_data_valid_json(self):
        data = self.sample_row_data["request_data_binary"]
        result = RequestReplayer.parse_request_data(data)
        self.assertEqual(result, {"name": "test"})

    def test_parse_request_data_invalid_json(self):
        result = RequestReplayer.parse_request_data(b"{bad json")
        self.assertIsNone(result)

    @patch("cli.apply_history_db.requests.request")
    def test_send_request_success(self, mock_request):
        mock_request.return_value.status_code = 200
        mock_request.return_value.ok = True
        replayer = RequestReplayer(
            db_man=MagicMock(),
            command_line_interface=MagicMock(),
            pretty=MagicMock(),
            conf=MagicMock(base_url="http://testserver", interactive=False, skip_request_errors=True)
        )
        result = replayer._RequestReplayer__send_request("http://testserver/api/test", "POST", json={"test": 1})
        self.assertEqual(result.status_code, 200)

if __name__ == "__main__":
    unittest.main()