from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from functools import wraps
import os
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# MySQL Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'my_music_mood'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def require_login(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def fetch_audiodb_data(endpoint, params=None):
    """Fetch data from TheAudioDB public API (free key = 123)."""
    base_url = "https://www.theaudiodb.com/api/v1/json/2"
    url = f"{base_url}/{endpoint}.php"
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"AudioDB API error: {e}")
        return {}


@app.route('/', methods=['GET', 'POST'])
def home():
    """Home page with user registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if not username or not email:
            flash('Please fill in all fields', 'error')
            return render_template('home.html')
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                # Check if email already exists
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    session['user_id'] = existing_user[0]
                    flash('Welcome back!', 'success')
                else:
                    # Create new user
                    cursor.execute(
                        "INSERT INTO users (username, email) VALUES (%s, %s)",
                        (username, email)
                    )
                    conn.commit()
                    session['user_id'] = cursor.lastrowid
                    flash('Registration successful!', 'success')
                
                cursor.close()
                conn.close()
                return redirect(url_for('songs'))
            except Error as e:
                flash(f'Database error: {str(e)}', 'error')
                conn.close()
        
        return render_template('home.html')
    
    # If user is already logged in, redirect to songs
    if 'user_id' in session:
        return redirect(url_for('songs'))
    
    return render_template('home.html')

@app.route('/profile', methods=['GET', 'POST'])
@require_login
def profile():
    """Display and edit user profile"""
    user_id = session['user_id']
    conn = get_db_connection()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET username = %s, email = %s WHERE user_id = %s",
                    (username, email, user_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('profile'))
            except Error as e:
                flash(f'Error updating profile: {str(e)}', 'error')
                if conn:
                    conn.close()
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, email, created_at FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                return render_template('profile.html', user={
                    'username': user[0],
                    'email': user[1],
                    'created_at': user[2]
                })
        except Error as e:
            flash(f'Error fetching profile: {str(e)}', 'error')
            if conn:
                conn.close()
    
    return render_template('profile.html', user=None)

@app.route('/search')
def search():
    """AJAX endpoint for song search with autocomplete"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    
    try:
        cursor = conn.cursor()
        search_query = f"%{query}%"
        cursor.execute("""
            SELECT s.song_id, s.title, a.name AS artist_name, s.song_coverphoto
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE s.title LIKE %s OR a.name LIKE %s
            LIMIT 10
        """, (search_query, search_query))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        songs = [{
            'song_id': row[0],
            'title': row[1],
            'artist': row[2],
            'coverphoto': row[3]
        } for row in results]
        
        return jsonify(songs)
    except Error as e:
        if conn:
            conn.close()
        return jsonify([])

@app.route('/song/<int:song_id>')
@require_login
def song_info(song_id):
    """Display song info and increment search count, merging with TheAudioDB"""
    user_id = session['user_id']
    conn = get_db_connection()
    
    if not conn:
        flash('Database connection error', 'error')
        return redirect(url_for('songs'))
    
    try:
        cursor = conn.cursor()
        
        # Get song details from your DB
        cursor.execute("""
            SELECT s.song_id, s.title, s.song_coverphoto, s.rating,
                   a.artist_id, a.name AS artist_name, a.artist_coverphoto,
                   l.language_id, l.language_name,
                   m.mood_id, m.mood_name
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            JOIN languages l ON s.language_id = l.language_id
            JOIN moods m ON s.mood_id = m.mood_id
            WHERE s.song_id = %s
        """, (song_id,))
        
        song = cursor.fetchone()
        
        if not song:
            flash('Song not found', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('songs'))
        
        # Increment search count
        cursor.execute("""
            INSERT INTO user_activity (user_id, song_id, search_count)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE 
                search_count = search_count + 1,
                last_searched = CURRENT_TIMESTAMP
        """, (user_id, song_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Base song data (from DB)
        song_data = {
            'song_id': song[0],
            'title': song[1],
            'song_coverphoto': song[2],
            'rating': float(song[3]),
            'artist_id': song[4],
            'artist_name': song[5],
            'artist_coverphoto': song[6],
            'language_id': song[7],
            'language_name': song[8],
            'mood_id': song[9],
            'mood_name': song[10]
        }

        # API metadata fetching is now handled asynchronously by the frontend via /api/track-metadata
        return render_template('song_info.html', song=song_data)
        
    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return redirect(url_for('songs'))

@app.route('/songs')
@require_login
def songs():
    """Show personalized recommendations and top songs with AudioDB details"""
    user_id = session['user_id']
    conn = get_db_connection()

    if not conn:
        flash('Database connection error', 'error')
        return render_template('songs.html', personalized=[], top_songs=[])

    try:
        cursor = conn.cursor()

        # Check user activity
        cursor.execute("SELECT COUNT(*) AS activity_count FROM user_activity WHERE user_id = %s", (user_id,))
        activity = cursor.fetchone()[0]

        personalized = []
        if activity > 0:
            # Get personalized recommendations
            cursor.execute("""
                SELECT DISTINCT s2.song_id, s2.title, s2.song_coverphoto,
                       a2.name AS artist_name, a2.artist_coverphoto, s2.rating, s2.youtube_link
                FROM user_activity ua
                JOIN songs s1 ON ua.song_id = s1.song_id
                JOIN songs s2 ON (s1.artist_id = s2.artist_id OR s1.mood_id = s2.mood_id)
                JOIN artists a2 ON s2.artist_id = a2.artist_id
                WHERE ua.user_id = %s AND s2.song_id NOT IN (
                    SELECT song_id FROM user_activity WHERE user_id = %s
                )
                ORDER BY s2.rating DESC
                LIMIT 10
            """, (user_id, user_id))

            personalized = [{
                'song_id': row[0],
                'title': row[1],
                'song_coverphoto': row[2],
                'artist_name': row[3],
                'artist_coverphoto': row[4],
                'rating': float(row[5]),
                'youtube_link': row[6]
            } for row in cursor.fetchall()]

        # Get overall top songs
        cursor.execute("""
            SELECT s.song_id, s.title, s.song_coverphoto,
                   a.name AS artist_name, a.artist_coverphoto, s.rating, s.youtube_link
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            ORDER BY s.rating DESC
            LIMIT 10
        """)

        top_songs = [{
            'song_id': row[0],
            'title': row[1],
            'song_coverphoto': row[2],
            'artist_name': row[3],
            'artist_coverphoto': row[4],
            'rating': float(row[5]),
            'youtube_link': row[6]
        } for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # 🔹 API metadata fetching is now handled asynchronously by the frontend via /api/track-metadata
        return render_template(
            'songs.html',
            personalized=personalized,
            top_songs=top_songs,
            has_activity=activity > 0
        )

        return render_template(
            'songs.html',
            personalized=personalized,
            top_songs=top_songs,
            has_activity=activity > 0
        )

    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return render_template('songs.html', personalized=[], top_songs=[])

@app.route('/languages')
@require_login
def languages():
    """Show top languages by user history and allow filtering"""
    user_id = session['user_id']
    language_id = request.args.get('id', type=int)
    conn = get_db_connection()
    
    if not conn:
        flash('Database connection error', 'error')
        return render_template('languages.html', top_languages=[], songs=[])
    
    try:
        cursor = conn.cursor()
        
        if language_id:
            # Get top songs by selected language
            cursor.execute("""
                SELECT s.song_id, s.title, s.song_coverphoto, 
                       a.name AS artist_name, a.artist_coverphoto,
                       l.language_name, s.rating, s.youtube_link
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                JOIN languages l ON s.language_id = l.language_id
                WHERE s.language_id = %s
                ORDER BY s.rating DESC
                LIMIT 10
            """, (language_id,))
            
            songs = [{
                'song_id': row[0],
                'title': row[1],
                'song_coverphoto': row[2],
                'artist_name': row[3],
                'artist_coverphoto': row[4],
                'language_name': row[5],
                'rating': float(row[6]),
                'youtube_link': row[7]
            } for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            return render_template('languages.html', top_languages=[], songs=songs, selected_language_id=language_id)
        
        # Get all languages, including those without history
        cursor.execute("""
            SELECT 
                l.language_id,
                l.language_name,
                COALESCE(SUM(ua.search_count), 0) AS total_searches
            FROM languages l
            LEFT JOIN songs s ON l.language_id = s.language_id
            LEFT JOIN user_activity ua ON s.song_id = ua.song_id AND ua.user_id = %s
            GROUP BY l.language_id, l.language_name
            ORDER BY total_searches DESC, l.language_name ASC
        """, (user_id,))
        
        top_languages = [{
            'language_id': row[0],
            'language_name': row[1],
            'total_searches': row[2]
        } for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('languages.html', top_languages=top_languages, songs=[])
        
    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return render_template('languages.html', top_languages=[], songs=[])

@app.route('/artists')
@require_login
def artists():
    """Show top artists by user history and allow filtering"""
    user_id = session['user_id']
    artist_id = request.args.get('id', type=int)
    conn = get_db_connection()
    
    if not conn:
        flash('Database connection error', 'error')
        return render_template('artists.html', top_artists=[], songs=[])
    
    try:
        cursor = conn.cursor()
        
        if artist_id:
            # Get top songs by selected artist
            cursor.execute("""
                SELECT s.song_id, s.title, s.song_coverphoto, s.rating, a.name as artist_name, s.youtube_link
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                WHERE s.artist_id = %s
                ORDER BY s.rating DESC
            """, (artist_id,))
            
            songs = [{
                'song_id': row[0],
                'title': row[1],
                'song_coverphoto': row[2],
                'rating': float(row[3]),
                'artist_name': row[4],
                'youtube_link': row[5]
            } for row in cursor.fetchall()]
            
            # Get artist info
            cursor.execute("SELECT name, artist_coverphoto FROM artists WHERE artist_id = %s", (artist_id,))
            artist_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return render_template('artists.html', top_artists=[], songs=songs, 
                                 selected_artist_id=artist_id, artist_name=artist_info[0] if artist_info else '')
        
        # Get all artists, including those without history
        cursor.execute("""
            SELECT 
                a.artist_id,
                a.name AS artist_name,
                a.artist_coverphoto,
                COALESCE(SUM(ua.search_count), 0) AS total_searches
            FROM artists a
            LEFT JOIN songs s ON a.artist_id = s.artist_id
            LEFT JOIN user_activity ua ON s.song_id = ua.song_id AND ua.user_id = %s
            GROUP BY a.artist_id, a.name, a.artist_coverphoto
            ORDER BY total_searches DESC, a.name ASC
        """, (user_id,))
        
        top_artists = [{
            'artist_id': row[0],
            'artist_name': row[1],
            'artist_coverphoto': row[2],
            'total_searches': row[3]
        } for row in cursor.fetchall()]

        # Artist API metadata fetching is now handled asynchronously by the frontend via /api/artist-metadata
        cursor.close()
        conn.close()
        
        return render_template('artists.html', top_artists=top_artists, songs=[])
        
        cursor.close()
        conn.close()
        
        return render_template('artists.html', top_artists=top_artists, songs=[])
        
    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return render_template('artists.html', top_artists=[], songs=[])

@app.route('/moods')
@require_login
def moods():
    """Show top moods by user history and allow filtering"""
    user_id = session['user_id']
    mood_id = request.args.get('id', type=int)
    conn = get_db_connection()
    
    if not conn:
        flash('Database connection error', 'error')
        return render_template('moods.html', top_moods=[], songs=[])
    
    try:
        cursor = conn.cursor()
        
        if mood_id:
            # Get top songs by selected mood
            cursor.execute("""
                SELECT s.song_id, s.title, s.song_coverphoto,
                       a.name AS artist_name, a.artist_coverphoto,
                       m.mood_name, s.rating, s.youtube_link
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                JOIN moods m ON s.mood_id = m.mood_id
                WHERE s.mood_id = %s
                ORDER BY s.rating DESC
                LIMIT 10
            """, (mood_id,))
            
            songs = [{
                'song_id': row[0],
                'title': row[1],
                'song_coverphoto': row[2],
                'artist_name': row[3],
                'artist_coverphoto': row[4],
                'mood_name': row[5],
                'rating': float(row[6]),
                'youtube_link': row[7]
            } for row in cursor.fetchall()]
            
            # Get mood info
            cursor.execute("SELECT mood_name FROM moods WHERE mood_id = %s", (mood_id,))
            mood_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return render_template('moods.html', top_moods=[], songs=songs, 
                                 selected_mood_id=mood_id, mood_name=mood_info[0] if mood_info else '')
        
        # Get all moods, including those without history
        cursor.execute("""
            SELECT 
                m.mood_id,
                m.mood_name,
                COALESCE(SUM(ua.search_count), 0) AS total_searches
            FROM moods m
            LEFT JOIN songs s ON m.mood_id = s.mood_id
            LEFT JOIN user_activity ua ON s.song_id = ua.song_id AND ua.user_id = %s
            GROUP BY m.mood_id, m.mood_name
            ORDER BY total_searches DESC, m.mood_name ASC
        """, (user_id,))
        
        top_moods = [{
            'mood_id': row[0],
            'mood_name': row[1],
            'total_searches': row[2]
        } for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('moods.html', top_moods=top_moods, songs=[])
        
    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return render_template('moods.html', top_moods=[], songs=[])

@app.route('/history')
@require_login
def history():
    """Show user's search history"""
    user_id = session['user_id']
    conn = get_db_connection()
    
    if not conn:
        flash('Database connection error', 'error')
        return render_template('history.html', history=[])
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.song_id, s.title, s.song_coverphoto,
                   a.name AS artist_name, a.artist_coverphoto,
                   ua.search_count, ua.last_searched, s.youtube_link
            FROM user_activity ua
            JOIN songs s ON ua.song_id = s.song_id
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE ua.user_id = %s
            ORDER BY ua.last_searched DESC
        """, (user_id,))
        
        history = [{
            'song_id': row[0],
            'title': row[1],
            'song_coverphoto': row[2],
            'artist_name': row[3],
            'artist_coverphoto': row[4],
            'search_count': row[5],
            'last_searched': row[6].strftime('%Y-%m-%d %H:%M'),
            'youtube_link': row[7]
        } for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('history.html', history=history)
        
    except Error as e:
        flash(f'Error: {str(e)}', 'error')
        if conn:
            conn.close()
        return render_template('history.html', history=[])

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# 🔹 New API Endpoints for Performance (Async Meta Fetching) 🔹

@app.route('/api/track-metadata/<int:song_id>')
def api_track_metadata(song_id):
    """Fetch track metadata (genre, thumbnails) from AudioDB and cache it"""
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'db error'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.title, a.name as artist_name, s.song_coverphoto 
            FROM songs s JOIN artists a ON s.artist_id = a.artist_id 
            WHERE s.song_id = %s
        """, (song_id,))
        song = cursor.fetchone()
        
        if not song:
            cursor.close(); conn.close()
            return jsonify({'error': 'not found'}), 404

        # Clean Strings for Search
        def clean_query(q):
            import re
            return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', q).strip()

        clean_title = clean_query(song['title'])
        clean_artist = clean_query(song['artist_name'])

        # Search AudioDB - Attempt 1: Artist + Title
        url = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?s={clean_artist}&t={clean_title}"
        r = requests.get(url, timeout=5)
        meta = {}
        track = None
        
        if r.status_code == 200:
            data = r.json()
            if data.get('track'):
                track = data['track'][0]
        
        # Search AudioDB - Attempt 2: Title only (Fallback if no track found)
        if not track:
            url_fallback = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?t={clean_title}"
            r_fb = requests.get(url_fallback, timeout=5)
            if r_fb.status_code == 200:
                data_fb = r_fb.json()
                if data_fb.get('track'):
                    # Pick the first track that matches common sense or just first link
                    track = data_fb['track'][0]

        if track:
            thumb = track.get('strTrackThumb') or track.get('strAlbumThumb')
            yt_link = track.get('strMusicVid')
            meta = {
                'genre': track.get('strGenre'),
                'album': track.get('strAlbum'),
                'year': track.get('intYearReleased'),
                'coverphoto': thumb,
                'youtube_link': yt_link
            }
            
            # Caching: Update DB if missing
            updates = []
            params = []
            if thumb and ('placeholder' in str(song['song_coverphoto']) or not song['song_coverphoto']):
                updates.append("song_coverphoto = %s")
                params.append(thumb)
            if yt_link:
                updates.append("youtube_link = %s")
                params.append(yt_link)
            
            if updates:
                params.append(song_id)
                cursor.execute(f"UPDATE songs SET {', '.join(updates)} WHERE song_id = %s", tuple(params))
                conn.commit()

        cursor.close(); conn.close()
        return jsonify(meta)
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/artist-metadata/<int:artist_id>')
def api_artist_metadata(artist_id):
    """Fetch artist thumbnail from AudioDB and cache it"""
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'db error'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, artist_coverphoto FROM artists WHERE artist_id = %s", (artist_id,))
        artist = cursor.fetchone()
        
        if not artist:
            cursor.close(); conn.close()
            return jsonify({'error': 'not found'}), 404

        # Clean Strings for Search
        def clean_query(q):
            import re
            return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', q).strip()

        clean_name = clean_query(artist['name'])

        # Search AudioDB - Attempt 1: Full name
        url = f"https://theaudiodb.com/api/v1/json/2/search.php?s={clean_name}"
        r = requests.get(url, timeout=5)
        meta = {}
        art = None
        
        if r.status_code == 200:
            data = r.json()
            if data.get('artists'):
                art = data['artists'][0]
        
        # Search AudioDB - Attempt 2: First word of name (Broad fallback)
        if not art and ' ' in clean_name:
            first_word = clean_name.split(' ')[0]
            url_fb = f"https://theaudiodb.com/api/v1/json/2/search.php?s={first_word}"
            r_fb = requests.get(url_fb, timeout=5)
            if r_fb.status_code == 200:
                data_fb = r_fb.json()
                if data_fb.get('artists'):
                    art = data_fb['artists'][0]

        if art:
            thumb = art.get('strArtistThumb') or art.get('strArtistLogo')
            meta = {'coverphoto': thumb}
            
            # Caching: Update DB if missing
            if thumb and ('placeholder' in str(artist['artist_coverphoto']) or not artist['artist_coverphoto']):
                cursor.execute("UPDATE artists SET artist_coverphoto = %s WHERE artist_id = %s", (thumb, artist_id))
                conn.commit()

        cursor.close(); conn.close()
        return jsonify(meta)
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

