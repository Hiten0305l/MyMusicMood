import os
import requests
import mysql.connector
import re
from dotenv import load_dotenv

def precache_song_metadata():
    load_dotenv()
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=os.getenv('DB_PORT')
        )
        cursor = conn.cursor(dictionary=True)
        
        print("Starting song metadata precaching...")
        cursor.execute("""
            SELECT s.song_id, s.title, a.name as artist_name, s.song_coverphoto, s.youtube_link 
            FROM songs s JOIN artists a ON s.artist_id = a.artist_id
        """)
        songs = cursor.fetchall()

        def clean_query(q):
            import re
            return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', q).strip()

        for song in songs:
            title = song['title']
            artist = song['artist_name']
            clean_title = clean_query(title)
            clean_artist = clean_query(artist)
            
            # Search AudioDB (Mimic the logic in app.py for consistency)
            # Try Artist + Title first
            url = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?s={clean_artist}&t={clean_title}"
            try:
                r = requests.get(url, timeout=5)
                track = None
                if r.status_code == 200:
                    data = r.json()
                    if data.get('track'):
                        track = data['track'][0]
                
                # Try Title only fallback
                if not track:
                    url_fb = f"https://theaudiodb.com/api/v1/json/2/searchtrack.php?t={clean_title}"
                    r_fb = requests.get(url_fb, timeout=5)
                    if r_fb.status_code == 200:
                        data_fb = r_fb.json()
                        if data_fb.get('track'):
                            track = data_fb['track'][0]

                if track:
                    thumb = track.get('strTrackThumb') or track.get('strAlbumThumb')
                    yt_link = track.get('strMusicVid')
                    
                    updates = []
                    params = []
                    if thumb and ('placeholder' in str(song['song_coverphoto']) or not song['song_coverphoto']):
                        updates.append("song_coverphoto = %s")
                        params.append(thumb)
                    if yt_link and (not song['youtube_link'] or str(song['youtube_link']) == 'None'):
                        updates.append("youtube_link = %s")
                        params.append(yt_link)
                    
                    if updates:
                        params.append(song['song_id'])
                        cursor.execute(f"UPDATE songs SET {', '.join(updates)} WHERE song_id = %s", tuple(params))
                        print(f"Updated song {title} by {artist}.")
            except Exception as e:
                print(f"Failed to fetch {title}: {e}")

        conn.commit()
        print("Precaching complete!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    precache_song_metadata()
