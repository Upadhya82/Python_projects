import pytest

from app import create_app
from models import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application with in-memory SQLite for tests."""
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "SECRET_KEY": "test-secret",
        }
    )
    yield test_app


@pytest.fixture(scope="function")
def db(app):
    """Set up and tear down the database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    return app.test_client()


@pytest.fixture
def admin_headers(client):
    """Register an admin user and return auth headers."""
    # Register
    client.post(
        "/api/users/register",
        json={
            "username": "adminuser",
            "email": "admin@example.com",
            "password": "adminpass123",
        },
    )
    from models import User

    with client.application.app_context():
        user = User.query.filter_by(username="adminuser").first()
        user.is_admin = True
        _db.session.commit()

    resp = client.post(
        "/api/users/login",
        json={"username": "adminuser", "password": "adminpass123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(client):
    """Register a regular user and return auth headers."""
    client.post(
        "/api/users/register",
        json={
            "username": "regularuser",
            "email": "user@example.com",
            "password": "userpass123",
        },
    )
    resp = client.post(
        "/api/users/login",
        json={"username": "regularuser", "password": "userpass123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
