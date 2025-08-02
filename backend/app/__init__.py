from flask import Flask
from dotenv import load_dotenv

# load enviornment vars from .env file
load_dotenv()

def create_app():
    # Create a new Flask app instance
    app = Flask(__name__)
    
    # Import and register the Pokedex blueprint
    from . import pokedex, auth
    app.register_blueprint(pokedex.bp)
    app.register_blueprint(auth.bp)
    
    
    return app
