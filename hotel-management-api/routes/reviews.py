from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from auth import get_current_user
from models import Booking, Hotel, Review, db

reviews_bp = Blueprint("reviews", __name__)


def _validate_review(data):
    errors = {}
    if not data.get("hotel_id"):
        errors["hotel_id"] = "hotel_id is required."
    rating = data.get("rating")
    if rating is None or not isinstance(rating, int) or not (1 <= rating <= 5):
        errors["rating"] = "Rating must be an integer between 1 and 5."
    return errors


def _refresh_hotel_rating(hotel_id):
    avg = db.session.query(func.avg(Review.rating)).filter_by(hotel_id=hotel_id).scalar()
    hotel = Hotel.query.get(hotel_id)
    if hotel:
        hotel.rating = round(float(avg), 2) if avg else 0.0
        db.session.commit()


@reviews_bp.route("", methods=["POST"])
@jwt_required()
def create_review():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    errors = _validate_review(data)
    if errors:
        return jsonify({"errors": errors}), 422

    hotel = Hotel.query.get(data["hotel_id"])
    if not hotel or not hotel.is_active:
        return jsonify({"error": "Hotel not found."}), 404

    # Only allow reviews from users who have completed a booking
    completed = (
        Booking.query.filter_by(user_id=user.id, hotel_id=hotel.id)
        .filter(Booking.status.in_(["confirmed", "completed"]))
        .first()
    )
    if not completed:
        return jsonify({"error": "You must have a booking at this hotel to leave a review."}), 403

    # One review per user per hotel
    if Review.query.filter_by(user_id=user.id, hotel_id=hotel.id).first():
        return jsonify({"error": "You have already reviewed this hotel."}), 409

    review = Review(
        user_id=user.id,
        hotel_id=hotel.id,
        rating=data["rating"],
        comment=data.get("comment", ""),
    )
    db.session.add(review)
    db.session.commit()
    _refresh_hotel_rating(hotel.id)

    return jsonify({"review": review.to_dict()}), 201


@reviews_bp.route("/<int:review_id>", methods=["PUT"])
@jwt_required()
def update_review(review_id):
    user = get_current_user()
    review = Review.query.get_or_404(review_id)

    if review.user_id != user.id and not user.is_admin:
        return jsonify({"error": "Access denied."}), 403

    data = request.get_json(silent=True) or {}
    if "rating" in data:
        rating = data["rating"]
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be an integer between 1 and 5."}), 422
        review.rating = rating
    if "comment" in data:
        review.comment = data["comment"]

    db.session.commit()
    _refresh_hotel_rating(review.hotel_id)
    return jsonify({"review": review.to_dict()}), 200


@reviews_bp.route("/<int:review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    user = get_current_user()
    review = Review.query.get_or_404(review_id)

    if review.user_id != user.id and not user.is_admin:
        return jsonify({"error": "Access denied."}), 403

    hotel_id = review.hotel_id
    db.session.delete(review)
    db.session.commit()
    _refresh_hotel_rating(hotel_id)
    return jsonify({"message": "Review deleted."}), 200


@reviews_bp.route("", methods=["GET"])
def list_reviews():
    hotel_id = request.args.get("hotel_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)

    query = Review.query
    if hotel_id:
        query = query.filter_by(hotel_id=hotel_id)

    paginated = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        {
            "reviews": [r.to_dict() for r in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
        }
    ), 200
