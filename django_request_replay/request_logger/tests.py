from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from request_logger.models import DjangoRequestsHistoryModel


class RequestHistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("view_requests_history_list")
        self.delete_url = reverse("delete_request_history")

    def _create_log_entry(self, method="POST", id_override=None):
        return DjangoRequestsHistoryModel.objects.create(
            request_method=method,
            request_path="/api/sim/queue/",
            request_data_text='{"command": "test"}',
            request_data_binary=b'{"command": "test"}',
            request_content_type="application/json",
            requester_useragent="TestAgent",
            requester_ip="127.0.0.1",
            requester_username="tester",
            response_code=200,
            response_data_text="success",
            label="test-entry"
        )

    def test_list_history_returns_entries(self):
        self._create_log_entry()
        self._create_log_entry()

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_history_with_id_filter(self):
        obj1 = self._create_log_entry()
        obj2 = self._create_log_entry()

        response = self.client.get(self.list_url, {"id__gte": obj2.id})
        self.assertEqual(response.status_code, 200)
        ids = [entry["id"] for entry in response.data]
        self.assertIn(obj2.id, ids)
        self.assertNotIn(obj1.id, ids)

    def test_delete_history(self):
        self._create_log_entry()

        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "history deleted")
        self.assertEqual(response.data["records_removed"], 1)
        self.assertEqual(DjangoRequestsHistoryModel.objects.count(), 0)
