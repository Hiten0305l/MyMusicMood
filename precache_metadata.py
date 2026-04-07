import os
import requests
import mysql.connector
import re
from dotenv import load_dotenv

def precache_artist_photos():
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
        
        print("Starting artist photo precaching...")
        cursor.execute("SELECT artist_id, name, artist_coverphoto FROM artists")
        artists = cursor.fetchall()

        for artist in artists:
            name = artist['name']
            clean_name = re.sub(r'\(.*?\)|\[.*?\]', '', name).strip()
            print(f"Searching for: {clean_name}...")
            
            # Search AudioDB (Mimic the logic in app.py for consistency)
            url = f"https://theaudiodb.com/api/v1/json/2/search.php?s={clean_name}"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('artists'):
                        art = data['artists'][0]
                        thumb = art.get('strArtistThumb') or art.get('strArtistLogo')
                        if thumb:
                            print(f"Found photo for {name}: {thumb}")
                            cursor.execute("UPDATE artists SET artist_coverphoto = %s WHERE artist_id = %s", (thumb, artist['artist_id']))
                        else:
                            print(f"No photo found for {name} in AudioDB results.")
                    else:
                        print(f"Artist {name} not found in AudioDB.")
            except Exception as e:
                print(f"Failed to fetch {name}: {e}")

        conn.commit()
        print("Precaching complete!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    precache_artist_photos()
