from flask import Flask
from dotenv import load_dotenv

# load enviornment vars from .env file
load_dotenv()

def create_app():
    # Create a new Flask app instance
    app = Flask(__name__)
    
    # Import and register the Pokedex view
    from . import pokedex
    app.register_blueprint(pokedex.bp)
    
    # Import and register the Battle view
    from . import battle
    app.register_blueprint(battle.bp)
    
    # Import and register the Gyms view
    from . import gym
    app.register_blueprint(gym.bp)
    
    return app
