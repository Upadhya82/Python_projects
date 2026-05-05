# Hotel Management API

A production-ready RESTful Hotel Management System built with **Flask**, **SQLAlchemy**, **JWT authentication**, and **Docker** support.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Docker Deployment](#docker-deployment)

---

## Features

- **JWT Authentication** – Secure token-based auth with refresh tokens
- **Password Hashing** – bcrypt for secure password storage
- **Role-Based Access Control** – Admin vs regular user permissions
- **Hotel CRUD** – Create, read, update, deactivate hotels
- **Booking Management** – Create, list, cancel bookings with availability checks
- **Review System** – Ratings (1–5) with automatic hotel rating recalculation
- **Payment Tracking** – Booking-linked payment records
- **Filtering & Sorting** – Hotels by location, price, rating, availability
- **Pagination** – All list endpoints support page/per_page
- **Input Validation** – Comprehensive field validation with descriptive errors
- **CORS Support** – Configurable allowed origins
- **Docker** – Multi-stage Dockerfile + docker-compose for PostgreSQL

---

## Project Structure

```
hotel-management-api/
├── app.py              # Flask application factory
├── config.py           # Environment-based configuration
├── models.py           # SQLAlchemy models (Hotel, User, Booking, Review, Payment)
├── auth.py             # JWT helpers, password hashing, admin decorator
├── routes/
│   ├── __init__.py     # Blueprint registration
│   ├── users.py        # /api/users  - register, login, profile
│   ├── hotels.py       # /api/hotels - CRUD, filtering, sorting
│   ├── bookings.py     # /api/bookings - create, list, cancel, payment
│   └── reviews.py      # /api/reviews - create, update, delete
├── tests/
│   ├── __init__.py
│   ├── conftest.py     # Pytest fixtures (app, db, client, headers)
│   ├── test_users.py
│   ├── test_hotels.py
│   └── test_bookings.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Local Setup (SQLite)

```bash
# Clone and enter the project
cd hotel-management-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
cp .env.example .env

# Start the development server
python app.py
```

The API is now running at `http://localhost:5000`.

---

## Environment Variables

Copy `.env.example` to `.env` and set:

| Variable        | Description                          | Default              |
|-----------------|--------------------------------------|----------------------|
| `SECRET_KEY`    | Flask secret key                     | dev key (insecure)   |
| `JWT_SECRET_KEY`| JWT signing key                      | dev key (insecure)   |
| `DATABASE_URL`  | SQLAlchemy DB connection string      | SQLite (local file)  |
| `FLASK_ENV`     | `development` / `production`         | `development`        |
| `CORS_ORIGINS`  | Allowed CORS origins                 | `*`                  |
| `PORT`          | HTTP port                            | `5000`               |

---

## API Reference

### Health Check

```
GET /health
```

---

### Users `/api/users`

| Method | Path           | Auth     | Description             |
|--------|----------------|----------|-------------------------|
| POST   | `/register`    | —        | Register new user       |
| POST   | `/login`       | —        | Login, receive tokens   |
| GET    | `/profile`     | JWT      | Get own profile         |
| PUT    | `/profile`     | JWT      | Update profile/password |
| GET    | `/`            | Admin    | List all users          |
| DELETE | `/<id>`        | Admin    | Deactivate user         |

**Register body:**
```json
{
  "username": "john",
  "email": "john@example.com",
  "password": "secret123",
  "full_name": "John Doe",
  "phone": "9876543210"
}
```

---

### Hotels `/api/hotels`

| Method | Path           | Auth     | Description             |
|--------|----------------|----------|-------------------------|
| GET    | `/`            | —        | List/filter/sort hotels |
| GET    | `/<id>`        | —        | Get hotel details       |
| POST   | `/`            | Admin    | Create hotel            |
| PUT    | `/<id>`        | Admin    | Update hotel            |
| DELETE | `/<id>`        | Admin    | Deactivate hotel        |
| GET    | `/<id>/reviews`| —        | List hotel reviews      |

**Query parameters for `GET /api/hotels`:**

| Param          | Type    | Description                           |
|----------------|---------|---------------------------------------|
| `location`     | string  | Filter by location (partial match)    |
| `min_price`    | float   | Minimum price per night               |
| `max_price`    | float   | Maximum price per night               |
| `min_rating`   | float   | Minimum average rating                |
| `available_only` | bool  | Only return hotels with rooms free    |
| `sort_by`      | string  | `name`, `price_per_night`, `rating`, `available_rooms` |
| `order`        | string  | `asc` (default) or `desc`             |
| `page`         | int     | Page number (default 1)               |
| `per_page`     | int     | Items per page (max 100)              |

---

### Bookings `/api/bookings`

| Method | Path                   | Auth  | Description                |
|--------|------------------------|-------|----------------------------|
| POST   | `/`                    | JWT   | Create booking             |
| GET    | `/`                    | JWT   | List bookings (own/all)    |
| GET    | `/<id>`                | JWT   | Get booking details        |
| POST   | `/<id>/cancel`         | JWT   | Cancel booking             |
| PUT    | `/<id>/payment`        | Admin | Update payment status      |

**Create booking body:**
```json
{
  "hotel_id": 1,
  "check_in": "2025-06-01",
  "check_out": "2025-06-05",
  "num_rooms": 2,
  "payment_method": "card"
}
```

Total cost is auto-calculated: `price_per_night × num_rooms × nights`.

---

### Reviews `/api/reviews`

| Method | Path    | Auth  | Description               |
|--------|---------|-------|---------------------------|
| POST   | `/`     | JWT   | Create review (needs booking) |
| PUT    | `/<id>` | JWT   | Update own review         |
| DELETE | `/<id>` | JWT   | Delete own review         |
| GET    | `/`     | —     | List reviews (filterable) |

**Create review body:**
```json
{
  "hotel_id": 1,
  "rating": 5,
  "comment": "Excellent stay!"
}
```

> A user must have an active/completed booking at the hotel to leave a review.

---

## Running Tests

```bash
cd hotel-management-api
pip install -r requirements.txt
pytest -v
```

Tests use an **in-memory SQLite** database and cover:
- User registration, login, profile management, admin controls
- Hotel CRUD, filtering, sorting, pagination
- Booking creation, cancellation, availability checks, access control

---

## Docker Deployment

### Start with Docker Compose (PostgreSQL)

```bash
cd hotel-management-api
cp .env.example .env   # Edit secrets!
docker-compose up --build
```

This starts:
- `db` – PostgreSQL 16
- `api` – Flask API served by Gunicorn on port `5000`

### Stop

```bash
docker-compose down
```

### Persistent data

PostgreSQL data is stored in the `postgres_data` Docker volume.

---

## Security Notes

- Change `SECRET_KEY` and `JWT_SECRET_KEY` before deploying to production.
- Use HTTPS in production (behind a reverse proxy like Nginx).
- Set `CORS_ORIGINS` to specific domains in production.
- Passwords are hashed with **bcrypt** (cost factor 12).
- SQL injection is prevented by SQLAlchemy's parameterized queries.
