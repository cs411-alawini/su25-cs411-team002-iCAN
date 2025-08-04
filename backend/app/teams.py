from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn


# Routes will go here e.g. @bp.route('/teams')
bp = Blueprint('teams', __name__, url_prefix='/teams', template_folder='templates')

# Create the endpoint at url_prefix='/teams'
@bp.route('/create', methods=['GET', 'POST'])
def create_team():
    """
    Display the create-a-team page. 
    """
    # Get values from sessions
    team = session.get('team', [])
    user_team_id = session.get('user_team_id')
    user_id = session.get('user_id')
    team_name = ""

    # We are editing an existing team, using information from
    # the database (redirect from Edit)
    if user_team_id and user_id:
        db_conn = getconn()
        try:
            with db_conn.cursor() as cursor:
                get_team_name = """
                    SELECT team_name 
                    FROM user_teams 
                    WHERE user_team_id = %s AND user_id = %s
                """
                cursor.execute(get_team_name,(user_team_id, user_id))
                team_name_results = cursor.fetchone()
                if team_name_results:
                    team_name = team_name_results["team_name"]
                    print(f"current team name is {team_name}")
                else:
                    team_name = ""
        finally:
            db_conn.close()

    # Search for a Pokemon (user pressed Search)
    if request.method == 'POST':
        # Get the search term (user input) from the form
        user_pokemon_input = request.form.get('pokemon_search', '').strip()

        results = []
        if user_pokemon_input:
            db_conn = getconn()
            try:
                with db_conn.cursor() as cursor:
                    get_pokemon_name = """
                        SELECT name 
                        FROM pokedex_entries 
                        WHERE LOWER(name) LIKE %s
                        LIMIT 10;
                    """
                    cursor.execute(get_pokemon_name, (f"%{user_pokemon_input.lower()}%",))
                    pokemon_name_results = cursor.fetchall()
            finally:
                db_conn.close()

        return render_template('create_team.html', pokemon_results=pokemon_name_results, team=team, team_name=team_name)

    # GET request, just render template with current team and no search results
    return render_template('create_team.html', team=team, team_name=team_name)



@bp.route('/add', methods=['POST'])
def add_pokemon():
    """
    Add pokemon to the current team in session.
    """
    pokemon = request.form.get('add_pokemon')
    if pokemon:
        team = session.get('team', [])
        # Team must be less than six pokemon and
        # user cannot have duplicates of the same
        # pokemon
        if len(team) < 6 and pokemon not in team:
            team.append(pokemon)
            session['team'] = team
    return redirect(url_for('teams.create_team'))


@bp.route('/update', methods=['POST'])
def update_team():
    """
    Update the team. Once the user presses "Save" for the team,
        we will delete the original pokemon on the team, but
        will maintain the same user team id.
    """
    user_team_id = session.get('user_team_id')
    if not user_team_id:
        return redirect(url_for('teams.create_team'))

    # Get user's new updated team from form
    new_updated_team = []
    for i in range(6):
        poke_name = request.form.get(f'pokemon{i}', '').strip()
        if poke_name:
            new_updated_team.append(poke_name)

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:

            print("We deleted the team.")

            # Delete pokemon on team to prepare for update
            delete_team = """
                DELETE 
                FROM user_poke_team_members 
                WHERE user_team_id = %s
            """
            cursor.execute(delete_team, (user_team_id,))

            # ---- SETUP variables to be looped through ----
            # Get the pokedex id of the pokemon chosen by user
            selected_pokedex_id = """
                SELECT pokedex_id 
                FROM pokedex_entries 
                WHERE LOWER(name) = %s LIMIT 1
            """
            # Add the pokemon chosen by user to database
            add_pokemon_to_team = """
                INSERT INTO user_poke_team_members (user_team_id, user_team_member_id, pokedex_id)
                VALUES (%s, %s, %s);
            """

            # Get the pokedex_id of the user's chosen pokemon and add it to current team
            # Add pokemon in order (0 to 6) in same way user set up team
            for team_order, poke_name in enumerate(new_updated_team):
                # Step 1: Get pokedex id
                cursor.execute(selected_pokedex_id, (poke_name.lower(),))
                pokedex_id_result = cursor.fetchone()
                if pokedex_id_result:
                    pokedex_id = pokedex_id_result['pokedex_id']
                    # Order the pokemon is on the team
                    user_team_member_id = team_order + 1
                    # Step 2: Add pokemon to team in database
                    cursor.execute(add_pokemon_to_team, (user_team_id, user_team_member_id, pokedex_id))
            db_conn.commit()

            print("We saved the team")
    finally:
        db_conn.close()

    # Save the team, just in case
    session['team'] = new_updated_team

    return redirect(url_for('home.load_teams'))



@bp.route('/save-name', methods=['POST', 'GET'])
def save_team_name():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            user_team_id = session.get('user_team_id')

            if request.method == 'POST':
                # Get team name that user wrote
                team_name = request.form.get('team_name', '').strip()
                session['team_name'] = team_name

                if user_team_id:
                    # Update existing team name in database
                    update_team_name = """
                        UPDATE user_teams
                        SET team_name = %s
                        WHERE user_team_id = %s AND user_id = %s
                    """
                    cursor.execute(update_team_name, (team_name, user_team_id, user_id))
                else:
                    # Create new team (and team name) in database
                    insert_new_team = """
                        INSERT INTO user_teams (user_id, team_name, is_active)
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_new_team, (user_id, team_name, 1))
                    user_team_id = cursor.lastrowid
                    session['user_team_id'] = user_team_id

                db_conn.commit()
                # Submit form, but stay on same html page
                # Now Edit vs Save in team name box logic happens
                return redirect(url_for('teams.create_team'))

            else:
                # GET (just page load) - load existing team name and pre-fill form information
                # when we just want to EDIT a team
                if user_team_id:
                    # Get the current team name
                    get_team = """
                        SELECT team_name 
                        FROM user_teams 
                        WHERE user_team_id = %s AND user_id = %s"
                    """
                    cursor.execute(get_team, (user_team_id, user_id))
                    get_team_result = cursor.fetchone()

                    # Determine what goes in the Team Name box
                    if get_team_result:
                        # Load a team name (previous team was made)
                        team_name = get_team_result[0]
                    else:
                        # Default in case something goes wrong with query
                        team_name = ""
                else:
                    # No existing team - empty input is default
                    team_name = ""

    finally:
        db_conn.close()

    # After saving a team name, stay on "create team" page
    return redirect(url_for('teams.create_team'))



@bp.route('/new', methods=['GET'])
def new_team():
    """
    Clear session and redirect to create team form with a blank slate.
        This is necessary to differentiate between creating a new
        team and updating an already exisiting team.
    """
    session.pop('team', None)
    session.pop('team_name', None)
    session.pop('user_team_id', None)
    return redirect(url_for('teams.create_team'))


@bp.route('/delete/<int:team_id>', methods=['POST'])
def delete_team(team_id):
    """
    The user has pressed the Delete button on the teams
        home page. This will delete the team in the 
        database, after making sure the team belongs
        to the user's user id.
    """
    # Make sure the user's id is still in session
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            # Ensure this team belongs to the user
            check_user_team = """
                SELECT user_id 
                FROM user_teams 
                WHERE user_team_id = %s
            """
            cursor.execute(check_user_team, (team_id,))
            check_user_team_result = cursor.fetchone()

            # Delete team
            if check_user_team_result and check_user_team_result['user_id'] == user_id:
                # First delete team members because of FK constraint
                delete_poke_members = """
                    DELETE 
                    FROM user_poke_team_members 
                    WHERE user_team_id = %s
                """
                cursor.execute(delete_poke_members, (team_id,))

                # After, delete team 
                delete_team = """
                    DELETE 
                    FROM user_teams 
                    WHERE user_team_id = %s
                """
                cursor.execute(delete_team, (team_id,))
                db_conn.commit()
    finally:
        db_conn.close()

    return redirect(url_for('home.load_teams'))



@bp.route('/edit/<int:team_id>', methods=['GET'])
def edit_team(team_id):
    """
    User has pressed Edit on the teams home page.
    """
    # Make sure that the user's id is still in session.
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            # Get the team name for the team the user wants to edit
            get_team_name = """
                SELECT team_name 
                FROM user_teams 
                WHERE user_team_id = %s AND user_id = %s
            """
            cursor.execute(get_team_name, (team_id, user_id))
            get_team_name_result = cursor.fetchone()
            if not get_team_name_result:
                return redirect(url_for('teams.load_teams'))

            # Load this information into session, just in case
            session['team_name'] = get_team_name_result['team_name']
            session['user_team_id'] = team_id

            # Get the Pokemon names on the team
            get_poke_names = """
                SELECT PE.name 
                FROM user_poke_team_members UPT JOIN pokedex_entries PE 
                    ON PE.pokedex_id = UPT.pokedex_id
                WHERE UPT.user_team_id = %s
                ORDER BY UPT.user_team_member_id ASC
            """
            cursor.execute(get_poke_names, (team_id,))
            poke_name_results = cursor.fetchall()
            team = []
            for pair in poke_name_results:
                team.append(pair['name'])
            session['team'] = team

    finally:
        db_conn.close()

    return redirect(url_for('teams.create_team'))
