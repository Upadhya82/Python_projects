from routes.bookings import bookings_bp
from routes.hotels import hotels_bp
from routes.reviews import reviews_bp
from routes.users import users_bp


def register_routes(app):
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(hotels_bp, url_prefix="/api/hotels")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
