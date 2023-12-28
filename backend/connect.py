import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Get the required information from environment variables
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(
        host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password
    )

    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Execute a sample SQL query
    cursor.execute("SELECT version();")

    # Fetch the result
    db_version = cursor.fetchone()
    print("PostgreSQL database version:", db_version)

except psycopg2.Error as e:
    print("Unable to connect to the database.")
    print(e)

finally:
    # Close the cursor and connection
    if conn:
        cursor.close()
        conn.close()
        print("Connection closed.")
