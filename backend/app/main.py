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
@bp.route('/battle', methods=['GET', 'POST'])
def load_battle():
    """
    Renders a form to select a team and gym leader (no Pokémon data shown).
    """
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))

    user_teams = []
    gyms = []
    selected_user_team_id = None
    selected_gym_id = None

    db_conn = getconn()
    try:
        with db_conn.cursor() as sql_cursor:
            # Get user's teams
            get_user_teams = """
                SELECT UT.user_team_id, UT.team_name
                FROM users U
                NATURAL JOIN user_teams UT
                WHERE U.user_name LIKE %s
            """
            sql_cursor.execute(get_user_teams, (f"%{username}%",))
            user_teams = sql_cursor.fetchall()

            # Get gym_leaders
            get_gym_leaders = """
                SELECT gym_id, gym_leader
                FROM gym_leaders
                ORDER BY gym_leader
            """
            sql_cursor.execute(get_gym_leaders)
            gym_leaders = sql_cursor.fetchall()

            # If the user submitted the form, store their selections (optional)
            if request.method == 'POST':
                selected_user_team_id = request.form.get('user_team_id')
                selected_gym_id = request.form.get('gym_id')

    finally:
        db_conn.close()

    return render_template(
        'battle.html',
        user_teams=user_teams,
        gyms=gym_leaders,
        selected_user_team_id=selected_user_team_id,
        selected_gym_id=selected_gym_id
    )


# Create the endpoint at url_prefix='/badges'
@bp.route('/badges', methods=['POST','GET'])
def load_badges():
    """
    The user has clicked the Badges button from homepage
    """
    username = session.get('username')
    user_id = session.get('user_id')

    if not username:
        return redirect(url_for('auth.login'))

    db_conn = getconn()

    all_gym_badges = []
    earned_badges = []

    try:
        with db_conn.cursor() as sql_cursor:

            # Get all badges for gyms
            get_badge_name = """
                SELECT badge_title
                FROM gym_leaders
            """
            sql_cursor.execute(get_badge_name)
            gym_badges_dict = sql_cursor.fetchall()
            for pair in gym_badges_dict:
                badge_title = pair['badge_title']
                all_gym_badges.append({
                    "name": badge_title,
                    "description": "",  
                    "image_filename": "badge.png"  
                })

            # Get a user's earned badges
            get_earned_badges = """
                SELECT DISTINCT GL.badge_title
                FROM (
                    SELECT gym_id, B.win_loss_outcome
                    FROM user_teams UT NATURAL JOIN battles B
                    WHERE B.win_loss_outcome = 1 AND UT.user_id = %s
                    GROUP BY gym_id
                ) AS gyms_won JOIN gym_leaders GL 
                ON gyms_won.gym_id = GL.gym_id
            """
            sql_cursor.execute(get_earned_badges, (user_id,))
            earned_badges_dict = sql_cursor.fetchall()
            for pair in earned_badges_dict:
                earned_badges.append(pair['badge_title']) 

    finally:
        db_conn.close()

    return render_template('badges.html', all_badges=all_gym_badges, earned_badges=earned_badges)
