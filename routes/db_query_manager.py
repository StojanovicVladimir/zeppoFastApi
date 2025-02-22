import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Retrieve the connection details from environment variables
host = os.getenv("HOST")
port = int(os.getenv("PORT"))
database = os.getenv("DATABASE")
username = os.getenv("DBUSERNAME")
password = os.getenv("PASSWORD")

# Create a SQLAlchemy engine
DATABASE_URL = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to execute query
def execute_query(query, values=None):
    # Create a new session for each call
    db = SessionLocal()
    try:
        # Use SQLAlchemy's text() for executing raw SQL queries
        result = db.execute(text(query), values)

        # If the query is a SELECT statement, fetch results
        if result.returns_rows:
            return result.fetchall()  # Fetch all results
        else:
            db.commit()  # Commit changes for non-returning queries
            return []  # Return an empty list for non-returning queries
    except Exception as e:
        print("An error occurred:", e)  # Print the error message
        db.rollback()  # Rollback in case of an error
        return []  # Return an empty list on error
    finally:
        db.close()  # Ensure the session is closed

