from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/login")
def login():
    return render_template("login.html")


@pages_bp.route("/register")
def register():
    return render_template("register.html")


@pages_bp.route("/onboarding")
def onboarding():
    return render_template("onboarding.html")


@pages_bp.route("/dashboard")
def dashboard():
    from flask import current_app
    return render_template(
        "dashboard.html",
        body_class="app-page",
        google_api_key=current_app.config.get("GOOGLE_API_KEY", ""),
    )


@pages_bp.route("/recommendations")
def recommendations():
    return render_template("recommendations.html", body_class="app-page")


@pages_bp.route("/itinerary")
def itinerary():
    return render_template("itinerary.html", body_class="app-page")


@pages_bp.route("/my-trips")
def my_trips():
    return render_template("my_trips.html", body_class="app-page")


@pages_bp.route("/wishlist")
def wishlist():
    return render_template("wishlist.html", body_class="app-page")


@pages_bp.route("/about")
def about():
    return render_template("about.html")


@pages_bp.route("/profile")
def profile():
    return render_template("profile.html", body_class="app-page")


@pages_bp.route("/chat")
def chat():
    return render_template("chat.html", body_class="app-page")
