from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from auth import admin_required, get_current_user
from models import Booking, Hotel, Payment, db

bookings_bp = Blueprint("bookings", __name__)


def _calculate_cost(hotel, check_in: date, check_out: date, num_rooms: int) -> float:
    nights = (check_out - check_in).days
    return round(hotel.price_per_night * num_rooms * nights, 2)


def _validate_booking(data):
    errors = {}
    for field in ("hotel_id", "check_in", "check_out"):
        if not data.get(field):
            errors[field] = f"{field} is required."
    try:
        check_in = date.fromisoformat(data.get("check_in", ""))
        check_out = date.fromisoformat(data.get("check_out", ""))
        if check_out <= check_in:
            errors["check_out"] = "Check-out must be after check-in."
        if check_in < date.today():
            errors["check_in"] = "Check-in cannot be in the past."
    except ValueError:
        errors.setdefault("check_in", "Invalid date format. Use YYYY-MM-DD.")
    num_rooms = data.get("num_rooms", 1)
    if not isinstance(num_rooms, int) or num_rooms < 1:
        errors["num_rooms"] = "num_rooms must be a positive integer."
    return errors


@bookings_bp.route("", methods=["POST"])
@jwt_required()
def create_booking():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    errors = _validate_booking(data)
    if errors:
        return jsonify({"errors": errors}), 422

    hotel = db.session.get(Hotel, data["hotel_id"])
    if not hotel or not hotel.is_active:
        return jsonify({"error": "Hotel not found."}), 404

    num_rooms = data.get("num_rooms", 1)
    if hotel.available_rooms < num_rooms:
        return jsonify({"error": f"Only {hotel.available_rooms} room(s) available."}), 409

    check_in = date.fromisoformat(data["check_in"])
    check_out = date.fromisoformat(data["check_out"])
    total_cost = _calculate_cost(hotel, check_in, check_out, num_rooms)

    booking = Booking(
        user_id=user.id,
        hotel_id=hotel.id,
        check_in=check_in,
        check_out=check_out,
        num_rooms=num_rooms,
        total_cost=total_cost,
        status="confirmed",
    )
    hotel.available_rooms -= num_rooms
    db.session.add(booking)
    db.session.flush()

    payment = Payment(
        booking_id=booking.id,
        amount=total_cost,
        status="pending",
        payment_method=data.get("payment_method", "card"),
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({"booking": booking.to_dict()}), 201


@bookings_bp.route("", methods=["GET"])
@jwt_required()
def list_bookings():
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)

    if user.is_admin:
        query = Booking.query
    else:
        query = Booking.query.filter_by(user_id=user.id)

    paginated = query.order_by(Booking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        {
            "bookings": [b.to_dict() for b in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
        }
    ), 200


@bookings_bp.route("/<int:booking_id>", methods=["GET"])
@jwt_required()
def get_booking(booking_id):
    user = get_current_user()
    booking = Booking.query.get_or_404(booking_id)
    if not user.is_admin and booking.user_id != user.id:
        return jsonify({"error": "Access denied."}), 403
    return jsonify({"booking": booking.to_dict()}), 200


@bookings_bp.route("/<int:booking_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_booking(booking_id):
    user = get_current_user()
    booking = Booking.query.get_or_404(booking_id)

    if not user.is_admin and booking.user_id != user.id:
        return jsonify({"error": "Access denied."}), 403
    if booking.status != "confirmed":
        return jsonify({"error": f"Booking is already {booking.status}."}), 409

    booking.status = "cancelled"
    hotel = db.session.get(Hotel, booking.hotel_id)
    if hotel:
        hotel.available_rooms += booking.num_rooms

    if booking.payment and booking.payment.status == "completed":
        booking.payment.status = "refunded"

    db.session.commit()
    return jsonify({"booking": booking.to_dict()}), 200


@bookings_bp.route("/<int:booking_id>/payment", methods=["PUT"])
@admin_required
def update_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not booking.payment:
        return jsonify({"error": "No payment record found."}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("pending", "completed", "refunded"):
        return jsonify({"error": "Invalid payment status."}), 422

    booking.payment.status = status
    if "transaction_id" in data:
        booking.payment.transaction_id = data["transaction_id"]
    db.session.commit()
    return jsonify({"payment": booking.payment.to_dict()}), 200
