from flask import Flask
from dotenv import load_dotenv

# load enviornment vars from .env file
load_dotenv()

def create_app():
    # Create a new Flask app instance
    app = Flask(__name__)
    
    app.secret_key = 'pikapika'

    # Import and register the Pokedex blueprint
    from . import pokedex, auth, main, teams, battle, gym
    app.register_blueprint(pokedex.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)    
    app.register_blueprint(teams.bp)
    app.register_blueprint(battle.bp)
    app.register_blueprint(gym.bp)
    
    return app
