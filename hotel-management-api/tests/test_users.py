import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/users/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "pass1234",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["user"]["username"] == "newuser"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_duplicate_username(self, client):
        payload = {"username": "dupeuser", "email": "a@example.com", "password": "pass1234"}
        client.post("/api/users/register", json=payload)
        payload2 = {"username": "dupeuser", "email": "b@example.com", "password": "pass1234"}
        resp = client.post("/api/users/register", json=payload2)
        assert resp.status_code == 409

    def test_register_duplicate_email(self, client):
        payload = {"username": "usera", "email": "shared@example.com", "password": "pass1234"}
        client.post("/api/users/register", json=payload)
        payload2 = {"username": "userb", "email": "shared@example.com", "password": "pass1234"}
        resp = client.post("/api/users/register", json=payload2)
        assert resp.status_code == 409

    def test_register_missing_fields(self, client):
        resp = client.post("/api/users/register", json={"username": "x"})
        assert resp.status_code == 422
        errors = resp.get_json()["errors"]
        assert "email" in errors or "password" in errors

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "validuser", "email": "v@example.com", "password": "123"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/users/register",
            json={"username": "logintest", "email": "lt@example.com", "password": "correct123"},
        )
        resp = client.post(
            "/api/users/login",
            json={"username": "logintest", "password": "correct123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_wrong_password(self, client):
        client.post(
            "/api/users/register",
            json={"username": "pwtest", "email": "pw@example.com", "password": "correct123"},
        )
        resp = client.post(
            "/api/users/login",
            json={"username": "pwtest", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/users/login",
            json={"username": "nobody", "password": "pass"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/users/login", json={})
        assert resp.status_code == 422


class TestProfile:
    def test_get_profile_authenticated(self, client, user_headers):
        resp = client.get("/api/users/profile", headers=user_headers)
        assert resp.status_code == 200
        assert resp.get_json()["user"]["username"] == "regularuser"

    def test_get_profile_unauthenticated(self, client):
        resp = client.get("/api/users/profile")
        assert resp.status_code == 401

    def test_update_profile(self, client, user_headers):
        resp = client.put(
            "/api/users/profile",
            json={"full_name": "Updated Name", "phone": "9876543210"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["user"]
        assert data["full_name"] == "Updated Name"
        assert data["phone"] == "9876543210"

    def test_update_password(self, client, user_headers):
        resp = client.put(
            "/api/users/profile",
            json={"password": "newpassword123"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        # Verify old login still works (by checking status with new password)
        login_resp = client.post(
            "/api/users/login",
            json={"username": "regularuser", "password": "newpassword123"},
        )
        assert login_resp.status_code == 200


class TestAdminUsers:
    def test_list_users_as_admin(self, client, admin_headers):
        resp = client.get("/api/users", headers=admin_headers)
        assert resp.status_code == 200
        assert "users" in resp.get_json()

    def test_list_users_as_regular(self, client, user_headers):
        resp = client.get("/api/users", headers=user_headers)
        assert resp.status_code == 403

    def test_list_users_unauthenticated(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401
