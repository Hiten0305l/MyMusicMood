import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def execute_sql_file(cursor, filename):
    with open(filename, 'r') as f:
        # Split by semicolon to get individual statements
        sqlCommands = f.read().split(';')
        for command in sqlCommands:
            # Skip empty commands or CREATE DATABASE/USE statements which aren't allowed in Aiven's defaultdb
            if command.strip() and not command.strip().upper().startswith('CREATE DATABASE') and not command.strip().upper().startswith('USE'):
                try:
                    cursor.execute(command)
                except Exception as e:
                    print(f"Error executing: {command[:50]}... \n Error: {e}")

try:
    print("Connecting to database...")
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor()
    
    print("Creating tables...")
    execute_sql_file(cursor, 'database_schema.sql')
    
    print("Inserting sample data (this might show errors if data already exists)...")
    execute_sql_file(cursor, 'sample_data.sql')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Successfully initialized database!")

except Exception as e:
    print(f"Failed to connect or initialize: {e}")
