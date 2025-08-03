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
    # Username and emails are stored in session from AUTH.PY
    username = session.get('username')
    email = session.get('email')
    user_id = session.get('user_id')

    # Setup to connect to GCP
    db_conn = getconn()

    # Stored procedure determines badge_level (novice, intermediate, advanced)
    badge_level = "unknown for now"
    # Get the number of badges earned
    badges_earned = "unknown for now"
    # Stored procedure determine win_loss_rate
    win_loss_rate = "unknown for now"
    # Stored procedure determines average_battle_time
    avg_battle_time = "unknown for now"
    try:
        # Open "context manager" for sql_cursor (auto-ends)
        with db_conn.cursor() as sql_cursor:
        
            # Set isolation level - we do not want write-write conflicts
            # There should only be unique usernames
            sql_cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")


            # Get the user's badge level
            get_badge_level = """
                SELECT badge_level
                FROM users 
                WHERE user_name LIKE %s;
            """ 
            sql_cursor.execute(get_badge_level, (f"%{username}%", ))
            badge_level_result = sql_cursor.fetchone()
            badge_level = badge_level_result['badge_level']


            # Get the number of badges earned by a user -- JOIN
            get_num_badges = """
                SELECT COUNT(DISTINCT B.gym_id) AS badge_nums
                FROM user_teams UT NATURAL JOIN battles B
                WHERE UT.user_id = %s AND B.win_loss_outcome = 1
            """
            sql_cursor.execute(get_num_badges, (user_id, ))
            num_badges_result = sql_cursor.fetchone()
            badges_earned = num_badges_result['badge_nums']


            # Get the percentage win/loss rate -- JOIN, GROUP BY
            get_win_rate = """
                SELECT ((COUNT(B2.battle_id) / total_battles.num_battles)*100) AS win_percentage
                FROM (
                    SELECT UT.user_id, COUNT(B.battle_id) AS num_battles
                    FROM user_teams UT NATURAL JOIN battles B
                    WHERE UT.user_id = %s
                    GROUP BY UT.user_id
                ) AS total_battles JOIN user_teams UT2 ON UT2.user_id = total_battles.user_id 
                JOIN battles B2 ON B2.user_team_id = UT2.user_team_id
                WHERE total_battles.user_id = %s AND B2.win_loss_outcome = 1 
                
            """
            sql_cursor.execute(get_win_rate, (user_id, user_id))
            win_rate_result = sql_cursor.fetchone()
            win_loss_rate = win_rate_result['win_percentage']
            print(f"win loss rate is = {win_rate_result}")


            # Get the average battle time
            get_avg_battle_time = """
                SELECT AVG(TIMESTAMPDIFF(MINUTE, B.start_time, B.end_time)) AS avg_time
                FROM user_teams UT NATURAL JOIN battles B
                WHERE UT.user_id = %s
            """
            sql_cursor.execute(get_avg_battle_time, (user_id, ))
            avg_battle_time_result = sql_cursor.fetchone()
            avg_battle_time = avg_battle_time_result['avg_time']
            print(f"Avg battle time result is = {avg_battle_time_result}")

    # Close connection to GCP
    finally:
            db_conn.close()
    

    return render_template('profile.html', user=username, badge_level=badge_level, 
                           email=email, win_loss_rate=win_loss_rate, avg_battle_time=avg_battle_time,
                           badges_earned=badges_earned)



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



# Create the endpoint at url_prefix='/badges'
@bp.route('/badges', methods=['POST','GET'])
def load_badges():
    """
    The user has clicked the Badges button from homepage
    """
    # Possible gym badges
    gym_badges = [
        {"name": "Explorer", "description": "Explore new places", "image_filename": "badge.png"},
        {"name": "Achiever", "description": "Complete difficult challenges", "image_filename": "badge.png"},
        {"name": "Helper", "description": "Help other users", "image_filename": "badge.png"},
        {"name": "Veteran", "description": "Use the app for 1 year", "image_filename": "badge.png"},
    ]

    # Example: badges this user has earned (you could get from DB)
    earned_badges = {"Explorer", "Helper"}  # Set for faster 'in' lookup

    return render_template('badges.html', all_badges=gym_badges, earned_badges=earned_badges)


