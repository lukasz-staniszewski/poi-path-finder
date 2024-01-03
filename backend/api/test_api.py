from unittest import TestCase

import pytest
from fastapi.testclient import TestClient

from backend.api import application

client = TestClient(application)


@pytest.mark.health
class TestApi(TestCase):
    def test_read_root(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello SPDB!"})

    def test_amenities(self):
        response = client.get("/amenities/")
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("amenities", response_data.keys())
        self.assertIsNotNone(response_data["amenities"])
        self.assertTrue(len(response_data["amenities"]) > 0)
        for amenity in response_data["amenities"]:
            self.assertIsInstance(amenity, str)
            self.assertIsNotNone(amenity)

    def test_create_route(self):
        test_route_details = {
            "start": {"latitude": 0.0, "longitude": 0.0},
            "end": {"latitude": 1.0, "longitude": 1.0},
            "additional_time": 10.0,
            "additional_distance": 5.0,
            "pois": [],
        }
        response = client.post("/route/", json=test_route_details)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("points", data)
        self.assertEqual(len(data["points"]), 2)  # Start + End
        self.assertEqual(data["path_time"], test_route_details["additional_time"])
        self.assertEqual(data["path_distance"], test_route_details["additional_distance"])
