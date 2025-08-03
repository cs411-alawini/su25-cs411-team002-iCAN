from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn

# Routes will go here e.g. @bp.route('/')
bp = Blueprint('home', __name__, url_prefix='/', template_folder='templates')


# Manage what HTML/route we're on
@bp.route('/')
def root():
    """
    An intermediate page to determine whether a user needs to re-login, or if they
        can load straight to the home page. This is necessary for dealing with 
        expired sessions.
    """
    # Deal with asking user to re-login
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('home.load_homepage'))

# Create the endpoint at url_prefix='/home'
@bp.route('/home', methods=['POST','GET'])
def load_homepage():
    """
    The user has logged in or signed up for the game and is now brought
        to the Pokemon Boss Rush Homepage.
    """
    username = session.get('username')
    return render_template('homepage.html', user=username)

# Create the endpoint at url_prefix='/profile'
@bp.route('/profile', methods=['POST','GET'])
def load_profile():
    """
    The user has clicked the Profile button from the homepage
    """
    username = session.get('username')
    return render_template('profile.html', user=username, badge_level="badge level")



# Create the endpoint at url_prefix='/teams'
@bp.route('/teams', methods=['POST','GET'])
def load_teams():
    """
    The user has clicked the Teams button from the homepage
    """

    # Username should already be stored in session
    username = session.get('username')


     # Setup to connect to GCP
    db_conn = getconn()
 

    try:
        # Open "context manager" for sql_cursor (auto-ends)
        with db_conn.cursor() as sql_cursor:
        
            # Set isolation level - we do not want write-write conflicts
            # There should only be unique usernames
            sql_cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")


            # Get the user's pokemon for each team
            get_team_pokemons = """
                SELECT UT.user_team_id, UT.team_name, PE.name AS pokedex_name
                FROM users U NATURAL JOIN user_teams UT JOIN user_poke_team_members UTP ON UT.user_team_id = UTP.user_team_id JOIN pokedex_entries PE ON PE.pokedex_id = UTP.pokedex_id 
                WHERE U.user_name LIKE %s;
            """ 
            sql_cursor.execute(get_team_pokemons, (f"%{username}%", ))
            team_pokemons = sql_cursor.fetchall()

    # Close connection to GCP
    finally:
            db_conn.close()

    # Organize pokemons by team_id for easy access in template
    teams_map = {}
    for row in team_pokemons:
        team_id = row['user_team_id']
        team_name = row['team_name']
        pokemon_name = row['pokedex_name']
        
        if team_id not in teams_map:
            teams_map[team_id] = {
                'team_id': team_id,
                'team_name': team_name,
                'pokemons': []
            }
        teams_map[team_id]['pokemons'].append(pokemon_name)

    teams_data = list(teams_map.values())
    return render_template('teams_home.html', teams=teams_data)




# Create the endpoint at url_prefix='/battle'
@bp.route('/battle', methods=['POST','GET'])
def load_battle():
    """
    The user has clicked the Enter Gym button from the homepage
    """

    return render_template('battle.html')

