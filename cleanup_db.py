import os
import mysql.connector
from dotenv import load_dotenv

def cleanup_database():
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
        
        print("Starting deduplication...")

        # 1. Deduplicate Moods
        cursor.execute("SELECT mood_name, MIN(mood_id) as master_id, COUNT(*) as cnt FROM moods GROUP BY mood_name HAVING cnt > 1")
        dupe_moods = cursor.fetchall()
        for mood in dupe_moods:
            print(f"Deduplicating mood: {mood['mood_name']} (Master ID: {mood['master_id']})")
            # Get all IDs for this mood name
            cursor.execute("SELECT mood_id FROM moods WHERE mood_name = %s AND mood_id != %s", (mood['mood_name'], mood['master_id']))
            extra_ids = [r['mood_id'] for r in cursor.fetchall()]
            
            # Remap songs
            for eid in extra_ids:
                cursor.execute("UPDATE songs SET mood_id = %s WHERE mood_id = %s", (mood['master_id'], eid))
            
            # Delete duplicates
            cursor.execute("DELETE FROM moods WHERE mood_name = %s AND mood_id != %s", (mood['mood_name'], mood['master_id']))

        # 2. Deduplicate Artists
        cursor.execute("SELECT name, MIN(artist_id) as master_id, COUNT(*) as cnt FROM artists GROUP BY name HAVING cnt > 1")
        dupe_artists = cursor.fetchall()
        for artist in dupe_artists:
            print(f"Deduplicating artist: {artist['name']} (Master ID: {artist['master_id']})")
            cursor.execute("SELECT artist_id FROM artists WHERE name = %s AND artist_id != %s", (artist['name'], artist['master_id']))
            extra_ids = [r['artist_id'] for r in cursor.fetchall()]
            
            # Remap songs
            for eid in extra_ids:
                cursor.execute("UPDATE songs SET artist_id = %s WHERE artist_id = %s", (artist['master_id'], eid))
            
            # Delete duplicates
            cursor.execute("DELETE FROM artists WHERE name = %s AND artist_id != %s", (artist['name'], artist['master_id']))

        # 3. Deduplicate Songs
        # Group by title AND artist_id (to handle same title different artist if it exists, though here they are identical)
        cursor.execute("SELECT title, artist_id, MIN(song_id) as master_id, COUNT(*) as cnt FROM songs GROUP BY title, artist_id HAVING cnt > 1")
        dupe_songs = cursor.fetchall()
        for song in dupe_songs:
            print(f"Deduplicating song: {song['title']} (Master ID: {song['master_id']})")
            # Remap activity
            cursor.execute("SELECT song_id FROM songs WHERE title = %s AND artist_id = %s AND song_id != %s", (song['title'], song['artist_id'], song['master_id']))
            extra_ids = [r['song_id'] for r in cursor.fetchall()]
            
            for eid in extra_ids:
                cursor.execute("UPDATE user_activity SET song_id = %s WHERE song_id = %s", (song['master_id'], eid))
            
            # Delete duplicates
            cursor.execute("DELETE FROM songs WHERE title = %s AND artist_id = %s AND song_id != %s", (song['title'], song['artist_id'], song['master_id']))

        conn.commit()
        print("Deduplication complete!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    cleanup_database()
