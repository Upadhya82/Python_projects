from datetime import date, timedelta

import pytest


HOTEL_PAYLOAD = {
    "name": "Booking Hotel",
    "location": "Chennai",
    "total_rooms": 10,
    "available_rooms": 10,
    "price_per_night": 100.0,
}


def _future(days):
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.fixture
def hotel_id(client, admin_headers):
    resp = client.post("/api/hotels", json=HOTEL_PAYLOAD, headers=admin_headers)
    return resp.get_json()["hotel"]["id"]


class TestCreateBooking:
    def test_create_booking_success(self, client, user_headers, hotel_id):
        resp = client.post(
            "/api/bookings",
            json={
                "hotel_id": hotel_id,
                "check_in": _future(1),
                "check_out": _future(3),
                "num_rooms": 2,
            },
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()["booking"]
        assert data["hotel_id"] == hotel_id
        assert data["num_rooms"] == 2
        assert data["total_cost"] == 2 * 100.0 * 2  # 2 rooms × $100 × 2 nights

    def test_create_booking_unauthenticated(self, client, hotel_id):
        resp = client.post(
            "/api/bookings",
            json={
                "hotel_id": hotel_id,
                "check_in": _future(1),
                "check_out": _future(2),
            },
        )
        assert resp.status_code == 401

    def test_create_booking_nonexistent_hotel(self, client, user_headers):
        resp = client.post(
            "/api/bookings",
            json={"hotel_id": 99999, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        assert resp.status_code == 404

    def test_create_booking_check_out_before_check_in(self, client, user_headers, hotel_id):
        resp = client.post(
            "/api/bookings",
            json={
                "hotel_id": hotel_id,
                "check_in": _future(5),
                "check_out": _future(2),
            },
            headers=user_headers,
        )
        assert resp.status_code == 422

    def test_create_booking_past_check_in(self, client, user_headers, hotel_id):
        resp = client.post(
            "/api/bookings",
            json={
                "hotel_id": hotel_id,
                "check_in": (date.today() - timedelta(days=1)).isoformat(),
                "check_out": _future(2),
            },
            headers=user_headers,
        )
        assert resp.status_code == 422

    def test_create_booking_no_rooms_available(self, client, user_headers, admin_headers):
        # Create hotel with only 1 room
        small_hotel = client.post(
            "/api/hotels",
            json={"name": "Tiny Inn", "location": "Delhi", "total_rooms": 1, "available_rooms": 1, "price_per_night": 50.0},
            headers=admin_headers,
        )
        h_id = small_hotel.get_json()["hotel"]["id"]
        # Book the one room
        client.post(
            "/api/bookings",
            json={"hotel_id": h_id, "check_in": _future(1), "check_out": _future(2), "num_rooms": 1},
            headers=user_headers,
        )
        # Try to book again
        resp = client.post(
            "/api/bookings",
            json={"hotel_id": h_id, "check_in": _future(1), "check_out": _future(2), "num_rooms": 1},
            headers=user_headers,
        )
        assert resp.status_code == 409

    def test_available_rooms_decrease_after_booking(self, client, user_headers, hotel_id):
        before = client.get(f"/api/hotels/{hotel_id}").get_json()["hotel"]["available_rooms"]
        client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2), "num_rooms": 3},
            headers=user_headers,
        )
        after = client.get(f"/api/hotels/{hotel_id}").get_json()["hotel"]["available_rooms"]
        assert after == before - 3


class TestCancelBooking:
    def test_cancel_booking(self, client, user_headers, hotel_id):
        create_resp = client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        booking_id = create_resp.get_json()["booking"]["id"]
        before_rooms = client.get(f"/api/hotels/{hotel_id}").get_json()["hotel"]["available_rooms"]

        cancel_resp = client.post(f"/api/bookings/{booking_id}/cancel", headers=user_headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.get_json()["booking"]["status"] == "cancelled"

        # Rooms should be restored
        after_rooms = client.get(f"/api/hotels/{hotel_id}").get_json()["hotel"]["available_rooms"]
        assert after_rooms == before_rooms + 1

    def test_cancel_already_cancelled(self, client, user_headers, hotel_id):
        create_resp = client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        booking_id = create_resp.get_json()["booking"]["id"]
        client.post(f"/api/bookings/{booking_id}/cancel", headers=user_headers)
        resp = client.post(f"/api/bookings/{booking_id}/cancel", headers=user_headers)
        assert resp.status_code == 409

    def test_cancel_other_users_booking(self, client, user_headers, admin_headers, hotel_id):
        # Create booking as regular user
        create_resp = client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        booking_id = create_resp.get_json()["booking"]["id"]
        # Try to cancel with admin (should succeed as admin)
        resp = client.post(f"/api/bookings/{booking_id}/cancel", headers=admin_headers)
        assert resp.status_code == 200


class TestListBookings:
    def test_user_sees_only_own_bookings(self, client, user_headers, hotel_id):
        client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        resp = client.get("/api/bookings", headers=user_headers)
        assert resp.status_code == 200
        assert resp.get_json()["total"] >= 1

    def test_admin_sees_all_bookings(self, client, user_headers, admin_headers, hotel_id):
        client.post(
            "/api/bookings",
            json={"hotel_id": hotel_id, "check_in": _future(1), "check_out": _future(2)},
            headers=user_headers,
        )
        resp = client.get("/api/bookings", headers=admin_headers)
        assert resp.status_code == 200

    def test_list_bookings_unauthenticated(self, client):
        resp = client.get("/api/bookings")
        assert resp.status_code == 401
