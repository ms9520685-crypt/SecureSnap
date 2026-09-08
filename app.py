from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from werkzeug.security import generate_password_hash, check_password_hash

from urllib.request import urlopen
from urllib.error import URLError

import logging
import os


app = Flask(__name__)

# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Secret key is taken from an environment variable.
# The fallback keeps the application usable locally.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///securesnap.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# --------------------------------------------------
# Security Logging
# --------------------------------------------------

logging.basicConfig(
    filename="security.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

security_logger = logging.getLogger("securesnap_security")


def log_security_event(event, username="anonymous"):
    ip_address = request.remote_addr

    security_logger.info(
        "EVENT=%s | USER=%s | IP=%s",
        event,
        username,
        ip_address
    )


# --------------------------------------------------
# Extensions
# --------------------------------------------------

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

csrf = CSRFProtect(app)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)


# --------------------------------------------------
# Database Models
# --------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )


class Photo(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(120),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    image_url = db.Column(
        db.String(500),
        nullable=False
    )


class Purchase(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    photo_id = db.Column(
        db.Integer,
        nullable=False
    )

    purchase_date = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


# --------------------------------------------------
# Login Manager
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------
# Photos
# --------------------------------------------------

@app.route("/photos")
@login_required
def photos():

    all_photos = Photo.query.all()

    return render_template(
        "photos.html",
        photos=all_photos
    )


# --------------------------------------------------
# Photo Details
# --------------------------------------------------

@app.route("/photo/<int:photo_id>")
@login_required
def photo_detail(photo_id):

    photo = Photo.query.get_or_404(photo_id)

    purchase = Purchase.query.filter_by(
        user_id=current_user.id,
        photo_id=photo.id
    ).first()

    purchased = purchase is not None

    return render_template(
        "photo_detail.html",
        photo=photo,
        purchased=purchased
    )


# --------------------------------------------------
# Purchase Photo
# --------------------------------------------------

@app.route(
    "/purchase/<int:photo_id>",
    methods=["POST"]
)
@login_required
def purchase(photo_id):

    photo = Photo.query.get_or_404(photo_id)

    existing_purchase = Purchase.query.filter_by(
        user_id=current_user.id,
        photo_id=photo.id
    ).first()

    if existing_purchase:

        log_security_event(
            "DUPLICATE_PURCHASE_ATTEMPT",
            current_user.username
        )

        return redirect(
            url_for(
                "photo_detail",
                photo_id=photo.id
            )
        )

    new_purchase = Purchase(
        user_id=current_user.id,
        photo_id=photo.id
    )

    db.session.add(new_purchase)
    db.session.commit()

    log_security_event(
        f"PHOTO_PURCHASE photo_id={photo.id}",
        current_user.username
    )

    return redirect(
        url_for(
            "photo_detail",
            photo_id=photo.id
        )
    )


# --------------------------------------------------
# Secure Photo Download
# --------------------------------------------------

@app.route("/download/<int:photo_id>")
@login_required
def download(photo_id):

    photo = Photo.query.get_or_404(photo_id)

    purchase = Purchase.query.filter_by(
        user_id=current_user.id,
        photo_id=photo.id
    ).first()

    # Block users who have not purchased the photo
    if not purchase:

        log_security_event(
            f"UNAUTHORIZED_DOWNLOAD_ATTEMPT photo_id={photo.id}",
            current_user.username
        )

        return Response(
            "Access denied. You must purchase this photo first.",
            status=403
        )

    try:

        image_data = urlopen(
            photo.image_url,
            timeout=10
        ).read()

        filename = (
            photo.title.replace(" ", "_")
            + ".jpg"
        )

        response = Response(
            image_data,
            mimetype="image/jpeg"
        )

        response.headers["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )

        log_security_event(
            f"AUTHORIZED_DOWNLOAD photo_id={photo.id}",
            current_user.username
        )

        return response

    except URLError:

        log_security_event(
            f"DOWNLOAD_ERROR photo_id={photo.id}",
            current_user.username
        )

        return Response(
            "Unable to download the image right now.",
            status=503
        )


# --------------------------------------------------
# Registration
# --------------------------------------------------

@app.route(
    "/register",
    methods=["GET", "POST"]
)
@limiter.limit(
    "5 per hour",
    methods=["POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # Required fields
        if not username or not password:

            log_security_event(
                "INVALID_REGISTRATION"
            )

            return (
                "Username and password are required.",
                400
            )

        # Username length validation
        if len(username) > 80:

            log_security_event(
                "REGISTRATION_USERNAME_TOO_LONG"
            )

            return (
                "Username is too long.",
                400
            )

        # Password length validation
        if len(password) < 8:

            log_security_event(
                "REGISTRATION_WEAK_PASSWORD",
                username
            )

            return (
                "Password must contain at least 8 characters.",
                400
            )

        # Check whether username already exists
        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            log_security_event(
                "DUPLICATE_REGISTRATION",
                username
            )

            return (
                "Username already exists.",
                409
            )

        # Hash password before storing it
        hashed_password = generate_password_hash(
            password
        )

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        log_security_event(
            "USER_REGISTERED",
            username
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# --------------------------------------------------
# Login
# --------------------------------------------------

@app.route(
    "/login",
    methods=["GET", "POST"]
)
@limiter.limit(
    "5 per minute",
    methods=["POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        # Successful login
        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            log_security_event(
                "SUCCESSFUL_LOGIN",
                username
            )

            return redirect(
                url_for("photos")
            )

        # Failed login
        log_security_event(
            "FAILED_LOGIN",
            username
        )

        return (
            "Invalid username or password.",
            401
        )

    return render_template(
        "login.html"
    )


# --------------------------------------------------
# Logout
# --------------------------------------------------

@app.route("/logout")
@login_required
def logout():

    username = current_user.username

    log_security_event(
        "USER_LOGOUT",
        username
    )

    logout_user()

    return redirect(
        url_for("index")
    )


# --------------------------------------------------
# Create Database + Sample Data
# --------------------------------------------------

with app.app_context():

    db.create_all()

    # Add sample photos only when database is empty
    if Photo.query.count() == 0:

        sample_photos = [

            Photo(
                title="Nature",
                description="Beautiful nature photography.",
                price=4.99,
                image_url=(
                    "https://images.unsplash.com/"
                    "photo-1500534623283-312aade485b7"
                )
            ),

            Photo(
                title="Workspace",
                description="Modern workspace photography.",
                price=5.99,
                image_url=(
                    "https://images.unsplash.com/"
                    "photo-1497366754035-f200968a6e72"
                )
            ),

            Photo(
                title="Technology",
                description="Technology and computer photography.",
                price=6.99,
                image_url=(
                    "https://images.unsplash.com/"
                    "photo-1518770660439-4636190af475"
                )
            )
        ]

        db.session.add_all(sample_photos)
        db.session.commit()


# --------------------------------------------------
# Run Application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)