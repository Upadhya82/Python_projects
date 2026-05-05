from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Hotel(db.Model):
    __tablename__ = "hotels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    location = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    total_rooms = db.Column(db.Integer, nullable=False, default=0)
    available_rooms = db.Column(db.Integer, nullable=False, default=0)
    price_per_night = db.Column(db.Float, nullable=False, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    amenities = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    bookings = db.relationship("Booking", back_populates="hotel", lazy="dynamic")
    reviews = db.relationship("Review", back_populates="hotel", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "description": self.description,
            "total_rooms": self.total_rooms,
            "available_rooms": self.available_rooms,
            "price_per_night": self.price_per_night,
            "rating": self.rating,
            "amenities": self.amenities,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Hotel {self.name}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), default="")
    phone = db.Column(db.String(20), default="")
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    bookings = db.relationship("Booking", back_populates="user", lazy="dynamic")
    reviews = db.relationship("Review", back_populates="user", lazy="dynamic")

    def to_dict(self, include_email=False):
        data = {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            data["email"] = self.email
        return data

    def __repr__(self):
        return f"<User {self.username}>"


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    num_rooms = db.Column(db.Integer, nullable=False, default=1)
    total_cost = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="confirmed",
    )  # confirmed, cancelled, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="bookings")
    hotel = db.relationship("Hotel", back_populates="bookings")
    payment = db.relationship("Payment", back_populates="booking", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "hotel_id": self.hotel_id,
            "hotel_name": self.hotel.name if self.hotel else None,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "num_rooms": self.num_rooms,
            "total_cost": self.total_cost,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Booking {self.id} User:{self.user_id} Hotel:{self.hotel_id}>"


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "hotel_id", name="uq_user_hotel_review"),
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )

    user = db.relationship("User", back_populates="reviews")
    hotel = db.relationship("Hotel", back_populates="reviews")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "hotel_id": self.hotel_id,
            "hotel_name": self.hotel.name if self.hotel else None,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Review {self.id} User:{self.user_id} Hotel:{self.hotel_id}>"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending"
    )  # pending, completed, refunded
    payment_method = db.Column(db.String(50), default="card")
    transaction_id = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    booking = db.relationship("Booking", back_populates="payment")

    def to_dict(self):
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "amount": self.amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Payment {self.id} Booking:{self.booking_id}>"
