from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from auth import admin_required, check_password, generate_tokens, get_current_user, hash_password
from models import User, db

users_bp = Blueprint("users", __name__)


def _validate_register(data):
    errors = {}
    if not data.get("username") or len(data["username"]) < 3:
        errors["username"] = "Username must be at least 3 characters."
    if not data.get("email") or "@" not in data["email"]:
        errors["email"] = "A valid email is required."
    if not data.get("password") or len(data["password"]) < 6:
        errors["password"] = "Password must be at least 6 characters."
    return errors


@users_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    errors = _validate_register(data)
    if errors:
        return jsonify({"errors": errors}), 422

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken."}), 409
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered."}), 409

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        full_name=data.get("full_name", ""),
        phone=data.get("phone", ""),
    )
    db.session.add(user)
    db.session.commit()

    tokens = generate_tokens(user.id)
    return jsonify({"user": user.to_dict(include_email=True), **tokens}), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 422

    user = User.query.filter_by(username=username).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials."}), 401

    if not user.is_active:
        return jsonify({"error": "Account is deactivated."}), 403

    tokens = generate_tokens(user.id)
    return jsonify({"user": user.to_dict(include_email=True), **tokens}), 200


@users_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict(include_email=True)}), 200


@users_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(silent=True) or {}

    if "full_name" in data:
        user.full_name = data["full_name"]
    if "phone" in data:
        user.phone = data["phone"]
    if "password" in data:
        if len(data["password"]) < 6:
            return jsonify({"error": "Password must be at least 6 characters."}), 422
        user.password_hash = hash_password(data["password"])

    db.session.commit()
    return jsonify({"user": user.to_dict(include_email=True)}), 200


@users_bp.route("", methods=["GET"])
@admin_required
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    paginated = User.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "users": [u.to_dict(include_email=True) for u in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
        }
    ), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({"message": "User deactivated."}), 200
