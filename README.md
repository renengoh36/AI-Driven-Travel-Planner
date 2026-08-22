# Pengo — AI-Driven Personalised Travel Planner

A Final Year Project: a travel planning web application that profiles users with K-Means
clustering, ranks attractions with a hybrid content-based + collaborative-filtering
recommendation engine, and generates optimised day-by-day itineraries — built to work
from a user's very first session despite having no prior interaction history (the
cold-start problem).

## Features

- **Onboarding & persona assignment** — budget, climate, and interest preferences encoded
  into a feature vector and matched to one of six traveller personas via K-Means clustering.
- **Hybrid recommendation engine** — combines content-based cosine similarity, persona-based
  feedback, user-based collaborative filtering, crowd-sourced rating, and popularity into a
  single weighted ranking, with a cold-start fallback for users with no rating history yet.
- **Live attraction data** — fetches real attraction data from the Google Places API on
  demand for destinations not already in the database.
- **Automated itinerary generation** — Haversine distance + Nearest Neighbour route
  optimisation, with category-aware time-slot scheduling.
- **Behavioural learning** — logs user interactions (searches, selections, itinerary
  generation, ratings) and uses them to refine future recommendations over time.
- **Chatbot** — conversational preference refinement (NLTK-based NLP, Groq/Llama for
  free-form assistance).
- **Wishlist, live weather, AI-generated packing lists, and nearby restaurant suggestions.**

## Tech Stack

Python 3.13 · Flask · SQLAlchemy · MySQL · scikit-learn · NumPy · bcrypt · NLTK ·
Groq (Llama) · Google Places API · Open-Meteo API

## Setup

1. **Clone and enter the project**
   ```
   git clone <repo-url>
   cd AI-Driven-Travel-Planner
   ```

2. **Create and activate a virtual environment**
   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment variables** — copy `.env.example` to `.env` and fill in real values:
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=travel_planner
   DB_USER=root
   DB_PASSWORD=your_mysql_password_here

   GOOGLE_API_KEY=your_google_api_key_here   # enable Places API + Geocoding API
   GROQ_API_KEY=your_groq_api_key_here        # console.groq.com

   FLASK_SECRET_KEY=change_this_to_a_random_string
   ```

5. **Create the MySQL database** (the app creates tables automatically on first run,
   but the database itself must already exist):
   ```sql
   CREATE DATABASE travel_planner;
   ```

6. **Run the app**
   ```
   python app.py
   ```
   Tables are created/migrated automatically on startup. Open **http://localhost:5000**
   in your browser. The server runs with `debug=True`, so code changes auto-reload.

## Running Tests

```
python -m unittest discover -s tests
```

Covers unit tests (K-Means profiling, hybrid recommendation scoring, behavioural weighting,
route optimisation, chatbot NLP, password hashing) and integration tests (full API request/
response flows against an in-memory SQLite database — no external MySQL needed to run them).

## Project Structure

```
app/
  __init__.py       Application factory — registers Blueprints, initialises extensions
  config.py         Flask configuration (database URI, secret key, API keys)
  models/           SQLAlchemy ORM models (users, attractions, itineraries, ...)
  routes/           Flask Blueprints — one per feature area
  modules/          Core logic: recommendation, profiling, behaviour, distance, chatbot
  templates/        Jinja2 HTML templates
  static/           CSS, JavaScript, images (including cached attraction photos)
data/
  kmeans_model.pkl  Pre-trained K-Means clustering model
scripts/            Evaluation and data-seeding utilities
tests/               Unit and integration tests
app.py              Entry point — creates tables and starts the dev server
fetch_attractions.py Google Places data-fetching pipeline
```

## Team

- **Ngoh Jia Ying** (24WMR08011) — AI/ML: user profiling, hybrid recommendation engine,
  behavioural learning, evaluation
- **Heng Qian Yu** — Itinerary generation & route optimisation, chatbot

Supervisor: Dr Lim Siew Mooi
