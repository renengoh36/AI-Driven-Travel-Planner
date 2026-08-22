from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
# Renders the main landing page.
def index():
    return render_template("index.html")


@pages_bp.route("/login")
# Renders the user login page.
def login():
    return render_template("login.html")


@pages_bp.route("/register")
# Renders the user registration page.
def register():
    return render_template("register.html")


@pages_bp.route("/onboarding")
 # Renders the user onboarding page.
def onboarding():
    return render_template("onboarding.html")


@pages_bp.route("/dashboard")
# Renders the main dashboard with the Google API key.
def dashboard():
    from flask import current_app
    return render_template(
        "dashboard.html",
        body_class="app-page",
        google_api_key=current_app.config.get("GOOGLE_API_KEY", ""),
    )


@pages_bp.route("/recommendations")
# Renders the personalised recommendations page.
def recommendations():
    return render_template("recommendations.html", body_class="app-page")


@pages_bp.route("/itinerary")
 # Renders the generated itinerary page.
def itinerary():
    return render_template("itinerary.html", body_class="app-page")


@pages_bp.route("/my-trips")
# Renders the user's saved travel history page.
def my_trips():
    return render_template("my_trips.html", body_class="app-page")


@pages_bp.route("/wishlist")
 # Renders the user's saved attractions wishlist page.
def wishlist():
    return render_template("wishlist.html", body_class="app-page")


@pages_bp.route("/about")
# Renders the system information page.
def about():
    return render_template("about.html")


@pages_bp.route("/profile")
# Renders the user's profile and preference page.
def profile():
    return render_template("profile.html", body_class="app-page")

@pages_bp.route("/chat")
# Renders the dedicated chatbot interface.
def chat():
    return render_template("chat.html", body_class="app-page")
