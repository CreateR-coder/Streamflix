import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# TMDB Configuration
API_KEY = "6363323958264147b046d7f77a16d48b"
BASE_URL = "https://api.themoviedb.org/3"

# Replace with your TMDB API Key or set environment variable TMDB_API_KEY
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", API_KEY)
TMDB_BASE_URL = BASE_URL

# In-memory storage for saved movies (demo purposes)
saved_movies = {}

def fetch_tmdb(endpoint, params=None):
    if params is None:
        params = {}
    params["api_key"] = TMDB_API_KEY
    try:
        response = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"TMDB API Error: {e}")
        return {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/home")
def get_home_data():
    trending = fetch_tmdb("/trending/movie/week").get("results", [])
    top_rated = fetch_tmdb("/movie/top_rated").get("results", [])
    action = fetch_tmdb("/discover/movie", {"with_genres": "28"}).get("results", [])
    
    return jsonify({
        "trending": trending,
        "top_rated": top_rated,
        "action": action
    })

@app.route("/api/top10")
def get_top10():
    data = fetch_tmdb("/trending/all/day")
    results = data.get("results", [])[:10]
    return jsonify(results)

@app.route("/api/category/<cat_id>")
def get_category(cat_id):
    page = request.args.get("page", 1, type=int)

    if cat_id == "saved_movies":
        return jsonify({"results": list(saved_movies.values())})

    genre_map = {
        "family_movies": ("/discover/movie", {"with_genres": "10751"}),
        "action_movies": ("/discover/movie", {"with_genres": "28"}),
        "comedy_movies": ("/discover/movie", {"with_genres": "35"}),
        "family_series": ("/discover/tv", {"with_genres": "10751"}),
        "action_series": ("/discover/tv", {"with_genres": "10759"}),
        "comedy_series": ("/discover/tv", {"with_genres": "35"}),
    }

    if cat_id in genre_map:
        endpoint, params = genre_map[cat_id]
        params["page"] = page
        data = fetch_tmdb(endpoint, params)
        return jsonify(data)

    return jsonify({"results": []})

@app.route("/api/search")
def search():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    data = fetch_tmdb("/search/multi", {"query": query})
    return jsonify(data.get("results", []))

@app.route("/api/movie/<int:movie_id>")
def get_movie_details(movie_id):
    data = fetch_tmdb(f"/movie/{movie_id}")
    # Add optional release details/age rating mocking
    data["age_rating"] = "13+"
    return jsonify(data)

@app.route("/api/tv/<int:tv_id>/seasons")
def get_tv_seasons(tv_id):
    data = fetch_tmdb(f"/tv/{tv_id}")
    return jsonify(data)

@app.route("/api/tv/<int:tv_id>/season/<int:season_num>")
def get_season_episodes(tv_id, season_num):
    data = fetch_tmdb(f"/tv/{tv_id}/season/{season_num}")
    return jsonify(data)

@app.route("/api/save_movie", methods=["POST"])
def save_movie():
    item = request.json
    if item and "id" in item:
        saved_movies[item["id"]] = item
        return jsonify({"status": "success", "saved_id": item["id"]})
    return jsonify({"status": "error"}), 400

@app.route("/api/track_click", methods=["POST"])
def track_click():
    item = request.json
    print(f"User clicked item: {item.get('title') or item.get('name')} (ID: {item.get('id')})")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
