from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# TMDB Configuration
API_KEY = "6363323958264147b046d7f77a16d48b"
BASE_URL = "https://api.themoviedb.org/3"

# In-memory storage for last searched items
last_searched_cache = []

def fetch_tmdb(endpoint, params=None):
    if params is None:
        params = {}
    params['api_key'] = API_KEY
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching from TMDB: {e}")
    return {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/home')
def get_home_data():
    """Returns content for the main Home tab."""
    trending_data = fetch_tmdb("/trending/movie/week")
    top_rated_data = fetch_tmdb("/movie/top_rated")
    action_data = fetch_tmdb("/discover/movie", {"with_genres": "28"})

    return jsonify({
        "trending": trending_data.get('results', []),
        "top_rated": top_rated_data.get('results', []),
        "action": action_data.get('results', [])
    })

@app.route('/api/top10')
def get_top10():
    """Returns the Top 10 Trending titles for today."""
    data = fetch_tmdb("/trending/all/day")
    results = data.get('results', [])
    return jsonify(results[:10])

@app.route('/api/category/<cat_type>')
def get_category(cat_type):
    """Fetches a single page of 20 items using TMDB pagination."""
    page = request.args.get('page', 1, type=int)

    category_map = {
        # Movies: Genres (Family: 10751, Action: 28, Comedy: 35)
        "family_movies": ("/discover/movie", {"with_genres": "10751", "sort_by": "popularity.desc"}),
        "action_movies": ("/discover/movie", {"with_genres": "28", "sort_by": "popularity.desc"}),
        "comedy_movies": ("/discover/movie", {"with_genres": "35", "sort_by": "popularity.desc"}),
        
        # Series/TV: Genres (Family: 10751, Action & Adventure: 10759, Comedy: 35)
        "family_series": ("/discover/tv", {"with_genres": "10751", "sort_by": "popularity.desc"}),
        "action_series": ("/discover/tv", {"with_genres": "10759", "sort_by": "popularity.desc"}),
        "comedy_series": ("/discover/tv", {"with_genres": "35", "sort_by": "popularity.desc"})
    }

    if cat_type == "last_searched":
        sorted_cache = sorted(
            last_searched_cache, 
            key=lambda x: x.get('popularity', 0), 
            reverse=True
        )
        return jsonify({"results": sorted_cache})

    if cat_type in category_map:
        endpoint, params = category_map[cat_type]
        params['page'] = page
        data = fetch_tmdb(endpoint, params)
        return jsonify({
            "results": data.get('results', []),
            "total_pages": min(data.get('total_pages', 1), 50)
        })

    return jsonify({"results": []})

@app.route('/api/search')
def search():
    """Searches TMDB and saves results into the last searched memory cache."""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    data = fetch_tmdb("/search/multi", {"query": query})
    results = data.get('results', [])
    
    for item in results:
        if item.get('media_type') in ['movie', 'tv']:
            if not any(cached['id'] == item['id'] for cached in last_searched_cache):
                last_searched_cache.append(item)

    return jsonify(results)

# --- NEW TV SHOW SEASON & EPISODE ENDPOINTS ---

@app.route('/api/tv/<int:tv_id>/seasons')
def get_tv_seasons(tv_id):
    """Fetches details for a TV series, including its seasons list."""
    data = fetch_tmdb(f"/tv/{tv_id}")
    seasons = data.get('seasons', [])
    # Filter out Season 0 (specials) if preferred, or keep all valid seasons
    valid_seasons = [s for s in seasons if s.get('season_number', 0) > 0]
    return jsonify({
        "name": data.get('name', 'TV Series'),
        "seasons": valid_seasons
    })

@app.route('/api/tv/<int:tv_id>/season/<int:season_num>')
def get_tv_episodes(tv_id, season_num):
    """Fetches all episodes for a specific season of a TV series."""
    data = fetch_tmdb(f"/tv/{tv_id}/season/{season_num}")
    episodes = data.get('episodes', [])
    return jsonify({
        "season_number": season_num,
        "episodes": episodes
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)