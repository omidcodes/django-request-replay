from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class CommandQueueSimulationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_enqueue_command(self):
        commands = ["restart wifi", "update firmware", "enable dhcp" , "disable dhcp"]
        for cmd in commands:
            url = reverse("enqueue_command")
            response = self.client.post(url, {"command": cmd}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["status"], "command added")
            self.assertEqual(response.data["command"], cmd)

        # Verify queue contents
        response = self.client.get(reverse("get_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["queue"], commands)

    def test_clear_queue(self):
        self.client.post(reverse("enqueue_command"), {"command": "test"}, format="json")
        response = self.client.delete(reverse("clear_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "queue cleared")

        # Ensure queue is empty
        response = self.client.get(reverse("get_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["queue"], [])
