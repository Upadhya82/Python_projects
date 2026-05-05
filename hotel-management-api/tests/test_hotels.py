import pytest


HOTEL_PAYLOAD = {
    "name": "Grand Palace",
    "location": "Bangalore",
    "description": "A luxury hotel",
    "total_rooms": 50,
    "price_per_night": 150.0,
    "rating": 4.5,
    "amenities": "WiFi, Pool, Spa",
}


class TestCreateHotel:
    def test_create_hotel_as_admin(self, client, admin_headers):
        resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.get_json()["hotel"]
        assert data["name"] == "Grand Palace"
        assert data["location"] == "Bangalore"
        assert data["total_rooms"] == 50

    def test_create_hotel_as_user_forbidden(self, client, user_headers):
        resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=user_headers)
        assert resp.status_code == 403

    def test_create_hotel_unauthenticated(self, client):
        resp = client.post("/api/hotels", json=HOTEL_PAYLOAD)
        assert resp.status_code == 401

    def test_create_hotel_duplicate_name(self, client, admin_headers):
        client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        assert resp.status_code == 409

    def test_create_hotel_missing_required_fields(self, client, admin_headers):
        resp = client.post(
            "/api/hotels",
            json={"description": "No name or location"},
            headers=admin_headers,
        )
        assert resp.status_code == 422
        errors = resp.get_json()["errors"]
        assert "name" in errors
        assert "location" in errors

    def test_create_hotel_negative_price(self, client, admin_headers):
        payload = dict(HOTEL_PAYLOAD, name="Cheap Hotel", price_per_night=-10)
        resp = client.post("/api/hotels", json=payload, headers=admin_headers)
        assert resp.status_code == 422


class TestListHotels:
    def _seed(self, client, admin_headers):
        hotels = [
            {"name": "Hotel Alpha", "location": "Bangalore", "total_rooms": 20, "price_per_night": 100.0},
            {"name": "Hotel Beta", "location": "Mumbai", "total_rooms": 30, "price_per_night": 200.0},
            {"name": "Hotel Gamma", "location": "Bangalore", "total_rooms": 10, "price_per_night": 80.0},
        ]
        for h in hotels:
            client.post("/api/hotels", json=h, headers=admin_headers)

    def test_list_all_hotels(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels")
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 3

    def test_filter_by_location(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels?location=Bangalore")
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 2

    def test_filter_by_max_price(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels?max_price=100")
        assert resp.status_code == 200
        for hotel in resp.get_json()["hotels"]:
            assert hotel["price_per_night"] <= 100

    def test_sort_by_price_desc(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels?sort_by=price_per_night&order=desc")
        assert resp.status_code == 200
        prices = [h["price_per_night"] for h in resp.get_json()["hotels"]]
        assert prices == sorted(prices, reverse=True)

    def test_pagination(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels?page=1&per_page=2")
        data = resp.get_json()
        assert len(data["hotels"]) == 2
        assert data["pages"] == 2

    def test_available_only_filter(self, client, admin_headers):
        self._seed(client, admin_headers)
        resp = client.get("/api/hotels?available_only=true")
        assert resp.status_code == 200
        for hotel in resp.get_json()["hotels"]:
            assert hotel["available_rooms"] > 0


class TestGetHotel:
    def test_get_existing_hotel(self, client, admin_headers):
        create_resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        hotel_id = create_resp.get_json()["hotel"]["id"]
        resp = client.get(f"/api/hotels/{hotel_id}")
        assert resp.status_code == 200
        assert resp.get_json()["hotel"]["id"] == hotel_id

    def test_get_nonexistent_hotel(self, client):
        resp = client.get("/api/hotels/99999")
        assert resp.status_code == 404


class TestUpdateHotel:
    def test_update_hotel(self, client, admin_headers):
        create_resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        hotel_id = create_resp.get_json()["hotel"]["id"]
        resp = client.put(
            f"/api/hotels/{hotel_id}",
            json={"price_per_night": 250.0},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["hotel"]["price_per_night"] == 250.0

    def test_update_hotel_forbidden(self, client, admin_headers, user_headers):
        create_resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        hotel_id = create_resp.get_json()["hotel"]["id"]
        resp = client.put(
            f"/api/hotels/{hotel_id}",
            json={"price_per_night": 250.0},
            headers=user_headers,
        )
        assert resp.status_code == 403


class TestDeleteHotel:
    def test_delete_hotel(self, client, admin_headers):
        create_resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
        hotel_id = create_resp.get_json()["hotel"]["id"]
        resp = client.delete(f"/api/hotels/{hotel_id}", headers=admin_headers)
        assert resp.status_code == 200
        # Hotel is deactivated, not visible in list
        list_resp = client.get("/api/hotels")
        hotel_ids = [h["id"] for h in list_resp.get_json()["hotels"]]
        assert hotel_id not in hotel_ids
