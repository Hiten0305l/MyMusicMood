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
    'database': os.getenv('DB_NAME', 'my_music_mood')
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
    base_url = "https://www.theaudiodb.com/api/v1/json/123"
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

        # 🔹 Fetch extra info from TheAudioDB
        try:
            query = song_data['title']
            artist = song_data['artist_name']
            api_url = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?s={artist}&t={query}"
            response = requests.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                if data and data.get("track"):
                    track = data["track"][0]
                    song_data.update({
                        'album': track.get('strAlbum'),
                        'genre': track.get('strGenre'),
                        'year': track.get('intYearReleased'),
                        'duration': track.get('intDuration'),
                        'description': track.get('strDescriptionEN'),
                        'track_thumb': track.get('strTrackThumb'),
                        'album_thumb': track.get('strAlbumThumb'),
                        'youtube_link': track.get('strMusicVid')
                    })
        except Exception as e:
            print(f"AudioDB fetch failed: {e}")
        
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
                       a2.name AS artist_name, a2.artist_coverphoto, s2.rating
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
                'rating': float(row[5])
            } for row in cursor.fetchall()]

        # Get overall top songs
        cursor.execute("""
            SELECT s.song_id, s.title, s.song_coverphoto,
                   a.name AS artist_name, a.artist_coverphoto, s.rating
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
            'rating': float(row[5])
        } for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # 🔹 Merge AudioDB Data for Personalized Songs
        for song in personalized:
            try:
                url = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?s={song['artist_name']}&t={song['title']}"
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('track'):
                        track = data['track'][0]
                        song.update({
                            'genre': track.get('strGenre'),
                            'album': track.get('strAlbum'),
                            'year': track.get('intYearReleased'),
                            'track_thumb': track.get('strTrackThumb'),
                            'album_thumb': track.get('strAlbumThumb')
                        })
                        # Prefer API cover photo if available
                        if not song['song_coverphoto'] and track.get('strTrackThumb'):
                            song['song_coverphoto'] = track['strTrackThumb']
            except Exception as e:
                print(f"AudioDB fetch failed (personalized): {e}")

        # 🔹 Merge AudioDB Data for Top Songs
        for song in top_songs:
            try:
                url = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?s={song['artist_name']}&t={song['title']}"
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('track'):
                        track = data['track'][0]
                        song.update({
                            'genre': track.get('strGenre'),
                            'album': track.get('strAlbum'),
                            'year': track.get('intYearReleased'),
                            'track_thumb': track.get('strTrackThumb'),
                            'album_thumb': track.get('strAlbumThumb')
                        })
                        track_thumb = track.get('strTrackThumb')
                        album_thumb = track.get('strAlbumThumb')

                        # Prefer API thumbnail if DB one is missing or invalid
                        if not song.get('song_coverphoto') or song['song_coverphoto'].strip() in ['', 'None', None]:
                            song['song_coverphoto'] = track_thumb or album_thumb or 'https://via.placeholder.com/300x300?text=No+Image'

                        # Keep for template compatibility
                        song['track_thumb'] = track_thumb
                        song['album_thumb'] = album_thumb

            except Exception as e:
                print(f"AudioDB fetch failed (top): {e}")

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
                       l.language_name, s.rating
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
                'rating': float(row[6])
            } for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            return render_template('languages.html', top_languages=[], songs=songs, selected_language_id=language_id)
        
        # Get top languages by user history
        cursor.execute("""
            SELECT 
                l.language_id,
                l.language_name,
                SUM(ua.search_count) AS total_searches
            FROM user_activity ua
            JOIN songs s ON ua.song_id = s.song_id
            JOIN languages l ON s.language_id = l.language_id
            WHERE ua.user_id = %s
            GROUP BY l.language_id, l.language_name
            ORDER BY total_searches DESC
        """, (user_id,))
        
        top_languages = [{
            'language_id': row[0],
            'language_name': row[1],
            'total_searches': row[2]
        } for row in cursor.fetchall()]
        
        # If no history, show all languages
        if not top_languages:
            cursor.execute("SELECT language_id, language_name FROM languages")
            top_languages = [{
                'language_id': row[0],
                'language_name': row[1],
                'total_searches': 0
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
                SELECT s.song_id, s.title, s.song_coverphoto, s.rating
                FROM songs s
                WHERE s.artist_id = %s
                ORDER BY s.rating DESC
            """, (artist_id,))
            
            songs = [{
                'song_id': row[0],
                'title': row[1],
                'song_coverphoto': row[2],
                'rating': float(row[3])
            } for row in cursor.fetchall()]
            
            # Get artist info
            cursor.execute("SELECT name, artist_coverphoto FROM artists WHERE artist_id = %s", (artist_id,))
            artist_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return render_template('artists.html', top_artists=[], songs=songs, 
                                 selected_artist_id=artist_id, artist_name=artist_info[0] if artist_info else '')
        
        # Get top artists by user history
        cursor.execute("""
            SELECT 
                a.artist_id,
                a.name AS artist_name,
                a.artist_coverphoto,
                SUM(ua.search_count) AS total_searches
            FROM user_activity ua
            JOIN songs s ON ua.song_id = s.song_id
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE ua.user_id = %s
            GROUP BY a.artist_id, a.name, a.artist_coverphoto
            ORDER BY total_searches DESC
        """, (user_id,))
        
        top_artists = [{
            'artist_id': row[0],
            'artist_name': row[1],
            'artist_coverphoto': row[2],
            'total_searches': row[3]
        } for row in cursor.fetchall()]
        
        # If no history, show all artists
        if not top_artists:
            cursor.execute("SELECT artist_id, name, artist_coverphoto FROM artists")
            top_artists = [{
                'artist_id': row[0],
                'artist_name': row[1],
                'artist_coverphoto': row[2],
                'total_searches': 0
            } for row in cursor.fetchall()]
        
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
                       m.mood_name, s.rating
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
                'rating': float(row[6])
            } for row in cursor.fetchall()]
            
            # Get mood info
            cursor.execute("SELECT mood_name FROM moods WHERE mood_id = %s", (mood_id,))
            mood_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return render_template('moods.html', top_moods=[], songs=songs, 
                                 selected_mood_id=mood_id, mood_name=mood_info[0] if mood_info else '')
        
        # Get top moods by user history
        cursor.execute("""
            SELECT 
                m.mood_id,
                m.mood_name,
                SUM(ua.search_count) AS total_searches
            FROM user_activity ua
            JOIN songs s ON ua.song_id = s.song_id
            JOIN moods m ON s.mood_id = m.mood_id
            WHERE ua.user_id = %s
            GROUP BY m.mood_id, m.mood_name
            ORDER BY total_searches DESC
        """, (user_id,))
        
        top_moods = [{
            'mood_id': row[0],
            'mood_name': row[1],
            'total_searches': row[2]
        } for row in cursor.fetchall()]
        
        # If no history, show all moods
        if not top_moods:
            cursor.execute("SELECT mood_id, mood_name FROM moods")
            top_moods = [{
                'mood_id': row[0],
                'mood_name': row[1],
                'total_searches': 0
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
                   ua.search_count, ua.last_searched
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
            'last_searched': row[6]
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

if __name__ == '__main__':
    app.run(debug=True)

