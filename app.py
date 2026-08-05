import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')

# TMDB Configuration
API_KEY = "6363323958264147b046d7f77a16d48b" # I hope this doesn't reveal stuff about me 
BASE_URL = "https://api.themoviedb.org/3"

# In-memory storage for saved movies and click tracking
saved_movies_db = {}
click_logs = []

def tmdb_get(endpoint, params=None):
    """Helper function to perform GET requests to TMDB API."""
    if params is None:
        params = {}
    params['api_key'] = API_KEY
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"TMDB Request Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/home', methods=['GET'])
def get_home_data():
    trending = tmdb_get('/trending/movie/day')
    top_rated = tmdb_get('/movie/top_rated')
    action = tmdb_get('/discover/movie', {'with_genres': '28', 'sort_by': 'popularity.desc'})

    return jsonify({
        'trending': trending.get('results', []) if trending else [],
        'top_rated': top_rated.get('results', []) if top_rated else [],
        'action': action.get('results', []) if action else []
    })

@app.route('/api/top10', methods=['GET'])
def get_top10():
    trending = tmdb_get('/trending/all/day')
    results = trending.get('results', []) if trending else []
    return jsonify(results[:10])

@app.route('/api/category/<category_name>', methods=['GET'])
def get_category(category_name):
    page = request.args.get('page', 1, type=int)

    if category_name == 'saved_movies':
        saved_list = list(saved_movies_db.values())
        return jsonify({'results': saved_list, 'page': 1, 'total_pages': 1})

    category_mapping = {
        'family_movies': ('/discover/movie', {'with_genres': '10751', 'sort_by': 'popularity.desc'}),
        'action_movies': ('/discover/movie', {'with_genres': '28', 'sort_by': 'popularity.desc'}),
        'comedy_movies': ('/discover/movie', {'with_genres': '35', 'sort_by': 'popularity.desc'}),
        'family_series': ('/discover/tv', {'with_genres': '10751', 'sort_by': 'popularity.desc'}),
        'action_series': ('/discover/tv', {'with_genres': '10759', 'sort_by': 'popularity.desc'}),
        'comedy_series': ('/discover/tv', {'with_genres': '35', 'sort_by': 'popularity.desc'})
    }

    if category_name not in category_mapping:
        return jsonify({'results': [], 'page': 1, 'total_pages': 0}), 400

    endpoint, params = category_mapping[category_name]
    params['page'] = page
    data = tmdb_get(endpoint, params)

    return jsonify({
        'results': data.get('results', []) if data else [],
        'page': data.get('page', 1) if data else 1,
        'total_pages': min(data.get('total_pages', 1), 50) if data else 1
    })

@app.route('/api/movie/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    movie_data = tmdb_get(f'/movie/{movie_id}', {'append_to_response': 'release_dates'})
    if not movie_data:
        return jsonify({'error': 'Movie not found'}), 404

    # Extract age rating from certification data
    age_rating = "NR"
    release_dates = movie_data.get('release_dates', {}).get('results', [])
    for country in release_dates:
        if country.get('iso_3166_1') == 'US':
            for release in country.get('release_dates', []):
                cert = release.get('certification')
                if cert:
                    age_rating = cert
                    break

    movie_data['age_rating'] = age_rating
    return jsonify(movie_data)

@app.route('/api/tv/<int:tv_id>/seasons', methods=['GET'])
def get_tv_seasons(tv_id):
    tv_data = tmdb_get(f'/tv/{tv_id}')
    if not tv_data:
        return jsonify({'error': 'TV show not found'}), 404
    return jsonify(tv_data)

@app.route('/api/tv/<int:tv_id>/season/<int:season_num>', methods=['GET'])
def get_tv_season_details(tv_id, season_num):
    season_data = tmdb_get(f'/tv/{tv_id}/season/{season_num}')
    if not season_data:
        return jsonify({'error': 'Season not found'}), 404
    return jsonify(season_data)

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    search_data = tmdb_get('/search/multi', {'query': query})
    results = search_data.get('results', []) if search_data else []
    
    # Filter out items without post-media types like person profiles
    filtered_results = [
        item for item in results 
        if item.get('media_type') in ['movie', 'tv'] or 'title' in item or 'name' in item
    ]
    return jsonify(filtered_results)

@app.route('/api/save_movie', methods=['POST'])
def save_movie():
    item = request.get_json()
    if not item or 'id' not in item:
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400

    saved_movies_db[item['id']] = item
    return jsonify({'status': 'success', 'saved_id': item['id']})

@app.route('/api/track_click', methods=['POST'])
def track_click():
    item = request.get_json()
    if item:
        click_logs.append(item)
    return jsonify({'status': 'logged'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
