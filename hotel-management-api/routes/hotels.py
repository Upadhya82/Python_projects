from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import asc, desc, func

from auth import admin_required
from models import Hotel, Review, db

hotels_bp = Blueprint("hotels", __name__)

SORTABLE_FIELDS = {"name", "location", "price_per_night", "rating", "available_rooms"}


def _validate_hotel(data, is_update=False):
    errors = {}
    if not is_update or "name" in data:
        if not data.get("name") or not data["name"].strip():
            errors["name"] = "Hotel name is required."
    if not is_update or "location" in data:
        if not data.get("location") or not data["location"].strip():
            errors["location"] = "Location is required."
    if not is_update or "price_per_night" in data:
        price = data.get("price_per_night")
        if price is None or not isinstance(price, (int, float)) or price < 0:
            errors["price_per_night"] = "A non-negative price per night is required."
    if not is_update or "total_rooms" in data:
        rooms = data.get("total_rooms")
        if rooms is None or not isinstance(rooms, int) or rooms < 0:
            errors["total_rooms"] = "Total rooms must be a non-negative integer."
    return errors


@hotels_bp.route("", methods=["GET"])
def list_hotels():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    location = request.args.get("location", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_rating = request.args.get("min_rating", type=float)
    sort_by = request.args.get("sort_by", "name")
    order = request.args.get("order", "asc").lower()
    available_only = request.args.get("available_only", "false").lower() == "true"

    query = Hotel.query.filter_by(is_active=True)

    if location:
        query = query.filter(Hotel.location.ilike(f"%{location}%"))
    if min_price is not None:
        query = query.filter(Hotel.price_per_night >= min_price)
    if max_price is not None:
        query = query.filter(Hotel.price_per_night <= max_price)
    if min_rating is not None:
        query = query.filter(Hotel.rating >= min_rating)
    if available_only:
        query = query.filter(Hotel.available_rooms > 0)

    if sort_by not in SORTABLE_FIELDS:
        sort_by = "name"
    sort_col = getattr(Hotel, sort_by)
    query = query.order_by(asc(sort_col) if order != "desc" else desc(sort_col))

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "hotels": [h.to_dict() for h in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
        }
    ), 200


@hotels_bp.route("/<int:hotel_id>", methods=["GET"])
def get_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    return jsonify({"hotel": hotel.to_dict()}), 200


@hotels_bp.route("", methods=["POST"])
@admin_required
def create_hotel():
    data = request.get_json(silent=True) or {}
    errors = _validate_hotel(data)
    if errors:
        return jsonify({"errors": errors}), 422

    if Hotel.query.filter_by(name=data["name"].strip()).first():
        return jsonify({"error": "A hotel with this name already exists."}), 409

    hotel = Hotel(
        name=data["name"].strip(),
        location=data["location"].strip(),
        description=data.get("description", ""),
        total_rooms=data["total_rooms"],
        available_rooms=data.get("available_rooms", data["total_rooms"]),
        price_per_night=data["price_per_night"],
        rating=data.get("rating", 0.0),
        amenities=data.get("amenities", ""),
    )
    db.session.add(hotel)
    db.session.commit()
    return jsonify({"hotel": hotel.to_dict()}), 201


@hotels_bp.route("/<int:hotel_id>", methods=["PUT"])
@admin_required
def update_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    data = request.get_json(silent=True) or {}
    errors = _validate_hotel(data, is_update=True)
    if errors:
        return jsonify({"errors": errors}), 422

    for field in ("name", "location", "description", "total_rooms", "available_rooms",
                  "price_per_night", "rating", "amenities"):
        if field in data:
            setattr(hotel, field, data[field])

    db.session.commit()
    _update_hotel_rating(hotel)
    return jsonify({"hotel": hotel.to_dict()}), 200


@hotels_bp.route("/<int:hotel_id>", methods=["DELETE"])
@admin_required
def delete_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    hotel.is_active = False
    db.session.commit()
    return jsonify({"message": "Hotel deactivated."}), 200


@hotels_bp.route("/<int:hotel_id>/reviews", methods=["GET"])
def get_hotel_reviews(hotel_id):
    Hotel.query.get_or_404(hotel_id)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    paginated = (
        Review.query.filter_by(hotel_id=hotel_id)
        .order_by(Review.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify(
        {
            "reviews": [r.to_dict() for r in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
        }
    ), 200


def _update_hotel_rating(hotel):
    avg = db.session.query(func.avg(Review.rating)).filter_by(hotel_id=hotel.id).scalar()
    hotel.rating = round(float(avg), 2) if avg else 0.0
    db.session.commit()
