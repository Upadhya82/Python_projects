from functools import wraps

import bcrypt
from flask import jsonify
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, get_jwt_identity, verify_jwt_in_request

from models import User, db

jwt = JWTManager()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_tokens(user_id: int):
    """Return a dict with access and refresh tokens for the given user id."""
    access_token = create_access_token(identity=str(user_id))
    refresh_token = create_refresh_token(identity=str(user_id))
    return {"access_token": access_token, "refresh_token": refresh_token}


def get_current_user():
    """Return the currently authenticated User object or None."""
    try:
        user_id = int(get_jwt_identity())
        return db.session.get(User, user_id)
    except Exception:
        return None


def admin_required(fn):
    """Decorator that requires the caller to be an authenticated admin user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if user is None or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper


@jwt.user_identity_loader
def user_identity_lookup(user):
    return str(user)


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return db.session.get(User, int(identity))
