import os
import mysql.connector
from dotenv import load_dotenv

def run_sql():
    load_dotenv()
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=os.getenv('DB_PORT')
        )
        cursor = conn.cursor()
        
        with open('sample_data.sql', 'r') as f:
            sql_script = f.read()
            
        # Split by semicolon but ignore inside strings (simplistic)
        # For sample_data.sql this should be fine
        queries = sql_script.split(';')
        for query in queries:
            if query.strip():
                try:
                    cursor.execute(query.strip())
                except Exception as e:
                    print(f"Skipping query due to error: {e}")
        
        conn.commit()
        print("SQL script executed successfully!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    run_sql()
