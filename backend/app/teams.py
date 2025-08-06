from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn


# Routes will go here e.g. @bp.route('/teams')
bp = Blueprint('teams', __name__, url_prefix='/teams', template_folder='templates')

# Create the endpoint at url_prefix='/teams'
@bp.route('/create', methods=['GET', 'POST'])
def create_team():
    """
    Display the create-a-team page. When the user presses the create a team
        button or the edit button, they will be directed here. If the user is
        editing a team, the team's user_team_id is already in session. If the
        user is creating a team for the first time, we require them to create
        a name first and SAVE the name. Doing so will create a record in the user_teams 
        relation, and will give us a user_team_id
    """
    # Deal with asking user to re-login
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    # Get value from sessions - from auth.py and main.py
    user_id = session.get('user_id')
    # If the user is creating a new team, there is nothing stored here
    # There are only values here if the user hit add, update, save team name or edit
    user_team_id = session.get('user_team_id')
    team = session.get('team', [])
    team_name = ""

    # We are editing an existing team, using information from
    # the database (redirect from update, edit, save team name)
    # ---------------------------------------------------------
    # This is true if user has hit other endpoints before this, 
    # like add, update, save team name or edit
    if user_team_id and user_id:
        # Connect to GCP
        db_conn = getconn()
        try:
            with db_conn.cursor() as cursor:
                # Get the user's team name based on current team_id stored
                # in session
                get_team_name = """
                    SELECT team_name 
                    FROM user_teams 
                    WHERE user_team_id = %s AND user_id = %s
                """
                cursor.execute(get_team_name,(user_team_id, user_id))
                team_name_results = cursor.fetchone()
                # We should only have one team name, specific to the 
                # team_id
                if team_name_results:
                    team_name = team_name_results["team_name"]
                    # DEBUG
                    # print(f"current team name is {team_name}")
                else:
                    team_name = ""
        finally:
            db_conn.close()

    # Search for a Pokemon (user pressed Search)
    if request.method == 'POST':
        # Get the search term (user input) from the form
        user_pokemon_input = request.form.get('pokemon_search', '').strip()

        # DEBUGGING
        # print("We are seraching for pokemon name")

        # Using the key/words the user inputting into the form,
        # search for the pokemon that have similar keys/words in it
        if user_pokemon_input:
            # Open BCP
            db_conn = getconn()
            try:
                with db_conn.cursor() as cursor:
                    # Get all the pokemon that have names/letters/words
                    # that contain what the user inputted into the form
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

        # Display the pokemon results for the pokemon search
        return render_template('create_team.html', pokemon_results=pokemon_name_results, team=team, team_name=team_name)

    # GET request, just render template with current team and no search results
    return render_template('create_team.html', team=team, team_name=team_name)



@bp.route('/add', methods=['POST'])
def add_pokemon():
    """
    Add pokemon to the current team in session. The team in session is the one
        the was just saved via save_team_name or the one that is being edited.
    """
    # The user searched for pokemon and pressed 'Add' from the
    # search results
    pokemon = request.form.get('add_pokemon')

    # Add the pokemon to the user's team
    if pokemon:
        # Grab the current team from update or edit team
        team = session.get('team', [])
        # Team must be less than six pokemon and cannot have duplicates
        if len(team) < 6 and pokemon not in team:
            team.append(pokemon)
            # Set the new 'team' in session
            session['team'] = team
    # Update the HTML page to show that we have added a pokemon to our team
    return redirect(url_for('teams.create_team'))


@bp.route('/update', methods=['POST'])
def update_team():
    """
    Update the team. Once the user presses the Edit team, they are brought to the 
        create-a-team HTML, with the pokemon and team name information displayed.
        IF the user is simply viewing the page, nothing happens to the record.
        But, once the user presses "Save" for the team, we will delete the 
        original user_team_id and save the new team with a new user_team_id.
    """
    # Get the user team id of the team they want to edit
    user_team_id = session.get('user_team_id')
    if not user_team_id:
        return redirect(url_for('teams.create_team'))

    # ---- SETUP PART 1 ----
    # Get user's new updated team from form, which they just
    # submitted
    new_updated_team = []
    for i in range(6):
        # Edit page sends us this information
        poke_name = request.form.get(f'pokemon{i}', '').strip()
        if poke_name:
            new_updated_team.append(poke_name)

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:

            # DEBUGGING
            # print("We deleted the team.")

            # Delete pokemon on team to prepare for update
            # The new updated team will have a new user_team_id
            delete_team = """
                DELETE 
                FROM user_poke_team_members 
                WHERE user_team_id = %s
            """
            cursor.execute(delete_team, (user_team_id,))

            # ---- SETUP PART 2 ----
            # Get the pokedex id of each pokemon chosen by user
            # by its name, in the new team (from new_updated_team)
            selected_pokedex_id = """
                SELECT pokedex_id 
                FROM pokedex_entries 
                WHERE LOWER(name) = %s LIMIT 1
            """

            # ---- SETUP PART 3 ----
            # Add the pokemon chosen by user to database as a new
            # record. User_team_id wil autoincrement itself
            add_pokemon_to_team = """
                INSERT INTO user_poke_team_members (user_team_id, user_team_member_id, pokedex_id)
                VALUES (%s, %s, %s);
            """

            # Assign user_team_member_id (0 to 6) to each pokemon in the new team
            for team_order, poke_name in enumerate(new_updated_team):
                # See SETUP PART 1 & 2
                cursor.execute(selected_pokedex_id, (poke_name.lower(),))
                pokedex_id_result = cursor.fetchone()
                # Assign order numbers
                if pokedex_id_result:
                    pokedex_id = pokedex_id_result['pokedex_id']
                    # This is the order number the pokemon is on the team
                    user_team_member_id = team_order + 1
                    # Add new pokemon to team in database
                    cursor.execute(add_pokemon_to_team, (user_team_id, user_team_member_id, pokedex_id))
            db_conn.commit()

            # DEBUGGING
            # print("We saved the team")
    finally:
        db_conn.close()

    # Save the team, in session to be used in later endpoints
    session['team'] = new_updated_team

    # Now that we've saved a team, choose each pokemon's moves
    return redirect(url_for('teams.choose_moves'))



@bp.route('/save-name', methods=['POST', 'GET'])
def save_team_name():
    """
    The user has pressed the create-a-team button on the teams homepage.
        In order for the user to save the team to the database, they must
        first save the team's name. This will create a record in the
        user_teams table, and will give us a user_team_id.
    The user MUST save a team name, before proceeding with making a team.
    """
    # Get the user_id from session so we can create FK connection
    # in user_teams relation
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Connect to GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:

            # If we are creating a new team, there will not be anything
            # stored in this.
            # If we are editing a team, there will be an id already stored
            # here. 
            # This determines whether or not the save-team-name button is
            # disabled or not.
            user_team_id = session.get('user_team_id')

            # User pressed the save team name button
            if request.method == 'POST':
                # Get team name that user wrote, from the form
                team_name = request.form.get('team_name', '').strip()
                # Set the team name is session
                session['team_name'] = team_name

                # The user is EDITING an already existing team's name
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
                    # Now, we have a record in the user_teams table and
                    # can create our team
                    session['user_team_id'] = user_team_id

                db_conn.commit()
                # Creating a new team name does not change the view, so we
                # stay on the create_team HTML
                return redirect(url_for('teams.create_team'))

            else:
                # GET request - we are just load existing team name and 
                # pre-filling out the form information on the right
                # This part is called when we are just EDITING a team, never
                # when we are creating a new team
                if user_team_id:
                    # Get the current team name
                    get_team = """
                        SELECT team_name 
                        FROM user_teams 
                        WHERE user_team_id = %s AND user_id = %s"
                    """
                    cursor.execute(get_team, (user_team_id, user_id))
                    get_team_result = cursor.fetchone()

                    # The results from the above query are displayed in the
                    # team name box
                    if get_team_result:
                        # Load a team name (previous team was made)
                        team_name = get_team_result[0]
                    else:
                        # Default in case something goes wrong with query
                        team_name = ""

                        # DEBUGGING
                        # print("See save_team_name(). We had a GET request, but no team name was saved. look into this error")
                else:
                    # No existing team - empty input is default
                    team_name = ""

                    #DEBUGGING
                    # print("See save_team_name(). We had a GET request, but could not find user_team_id. You may need to add redirect to auth")

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
    # We are not editing a team. We are creating a new team, so start new sessions!
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
            # Ensure this team belongs to the user (safety measure)
            check_user_team = """
                SELECT user_id 
                FROM user_teams 
                WHERE user_team_id = %s
            """
            cursor.execute(check_user_team, (team_id,))
            check_user_team_result = cursor.fetchone()

            # Delete team if query is successful and user is indeed the user
            if check_user_team_result and check_user_team_result['user_id'] == user_id:
                # First, delete team members because of FK constraint
                delete_poke_members = """
                    DELETE 
                    FROM user_poke_team_members 
                    WHERE user_team_id = %s
                """
                cursor.execute(delete_poke_members, (team_id,))

                # After deleting pokemon on team, delete the team record in user_teams
                delete_team = """
                    DELETE 
                    FROM user_teams 
                    WHERE user_team_id = %s
                """
                cursor.execute(delete_team, (team_id,))
                db_conn.commit()
    finally:
        db_conn.close()

    # We deleted from the load_teams page, so stay on page
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
            # user_team_id comes from HTML
            get_team_name = """
                SELECT team_name 
                FROM user_teams 
                WHERE user_team_id = %s AND user_id = %s
            """
            cursor.execute(get_team_name, (team_id, user_id))
            get_team_name_result = cursor.fetchone()

            # There was an error running the query.
            if not get_team_name_result:
                # DEBUGGING
                # print("See edit_team(). There was no matching team name in the db. Look into this error.")
                return redirect(url_for('teams.load_teams'))

            # Load the team name and team id of the team we want to edit into SESSION
            # This is important for Jinja to load the correct tema details
            session['team_name'] = get_team_name_result['team_name']
            session['user_team_id'] = team_id

            # Get the Pokemon names on the team we want to edit
            get_poke_names = """
                SELECT PE.name 
                FROM user_poke_team_members UPT JOIN pokedex_entries PE 
                    ON PE.pokedex_id = UPT.pokedex_id
                WHERE UPT.user_team_id = %s
                ORDER BY UPT.user_team_member_id ASC
            """
            cursor.execute(get_poke_names, (team_id,))
            poke_name_results = cursor.fetchall()

            # Just grab the names from the result dictionary
            team = []
            for pair in poke_name_results:
                team.append(pair['name'])
            
            # Store the pokemon names on the team in session for Jinja
            session['team'] = team

    finally:
        db_conn.close()

    # Editing a team will redirect to the create a team page
    # With the session information prefilled out on the page
    return redirect(url_for('teams.create_team'))


@bp.route("/choose_moves", methods=['GET'])
def choose_moves():
    """
    After the user has created a new team, or saved their edit to a team, we
        will then force the user to choose new moves or choose moves for the pokemon
        on the team.
    """
    # This should have been set from the create a team page.
    user_team_id = session.get('user_team_id')
    if not user_team_id:
        return redirect(url_for('teams.create_team'))

    # Open GCP
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            # Get the pokedex_id and name for each Pokemon on the user's team
            get_team_query = """
                SELECT PE.pokedex_id, PE.name
                FROM user_poke_team_members UPT
                JOIN pokedex_entries PE ON UPT.pokedex_id = PE.pokedex_id
                WHERE UPT.user_team_id = %s
                ORDER BY UPT.user_team_member_id ASC
            """
            cursor.execute(get_team_query, (user_team_id,))
            team_pokemon = cursor.fetchall()

            # For each Pokeon, get its available moves (all move info)
            moves_by_pokemon = []
            for poke in team_pokemon:
                # Know which pokemon to look at
                pokedex_id = poke['pokedex_id']
                name = poke['name']
                
                # Get all moves possible for that specific pokemon
                get_moves_query = """
                    SELECT M.move_name, M.move_type, M.category, M.move_power, M.accuracy, M.pp
                    FROM pokemon_moves PM
                    JOIN moves M ON PM.move_id = M.move_id
                    WHERE PM.pokedex_id = %s
                    ORDER BY M.move_name
                """
                cursor.execute(get_moves_query, (pokedex_id,))
                move_results = cursor.fetchall()  

                # Grab the move information for Jinja
                moves_by_pokemon.append({
                    'name': name,
                    'pokedex_id': pokedex_id,
                    'moves': move_results 
                })

    finally:
        db_conn.close()

    # Display all the moves and move information for Jinja
    # This will be displayed as cards
    return render_template('moves.html', moves_by_pokemon=moves_by_pokemon)


@bp.route('/save_moves', methods=['POST'])
def save_moves():
    """
    The user has finished selecting moves for their pokemon. Now, we need 
        to save the move_ids to the database and tie them to the team pokemon.
    """

    # This should have been saved from the create team page
    user_team_id = session.get('user_team_id')
    if not user_team_id:
        return redirect(url_for('teams.create_team'))

    # Connect to DB
    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            # Get the team members in order with their user_team_member_id and pokedex_id
            # Remember that team_members are order 0 - 6, up until the number of pokemon
            # that are on the team
            get_team_members = """
                SELECT user_team_member_id, pokedex_id
                FROM user_poke_team_members
                WHERE user_team_id = %s
                ORDER BY user_team_member_id ASC
            """
            cursor.execute(get_team_members, (user_team_id,))
            team_members = cursor.fetchall()

            # Look at each pokemon on the team, then look at their moves
            # Save this information in the database in the user_poke_team_memebrs
            # relation. The user_team_id is the FK for each record.
            for member in team_members:
                # Look at one pokemon on the team
                member_id = member['user_team_member_id']
                pokedex_id = member['pokedex_id']

                # Get moves selected by user for this pokemon
                selected_moves = request.form.getlist(f"moves_{pokedex_id}")

                # Users can only have four moves per pokemon
                if len(selected_moves) != 4:
                    # Error handling
                    return "Please select exactly 4 moves for each Pokémon.", 400

                # Setup variables to store query results in
                move_ids = []
                move_pps = []

                # Look at ALL the selected moves for one pokemon
                for move_name in selected_moves:
                    # For each move name, get move_id and initial current_pp from moves table
                    cursor.execute("SELECT move_id, pp FROM moves WHERE move_name = %s", (move_name,))
                    move_row = cursor.fetchone()
                    # Store this information in variables
                    if move_row:
                        move_ids.append(move_row['move_id'])
                        move_pps.append(move_row['pp'])
                    else:
                        # Move not found, handle error or skip
                        return f"Move '{move_name}' not found.", 400

                # Update the user_poke_team_members row for this Pokemon with the chosen moves and their PP
                update_moves_sql = """
                    UPDATE user_poke_team_members
                    SET move_1_id = %s, move_1_current_pp = %s,
                        move_2_id = %s, move_2_current_pp = %s,
                        move_3_id = %s, move_3_current_pp = %s,
                        move_4_id = %s, move_4_current_pp = %s
                    WHERE user_team_id = %s AND user_team_member_id = %s
                """
                cursor.execute(update_moves_sql, (
                    move_ids[0], move_pps[0],
                    move_ids[1], move_pps[1],
                    move_ids[2], move_pps[2],
                    move_ids[3], move_pps[3],
                    user_team_id, member_id
                ))

            db_conn.commit()

    finally:
        db_conn.close()
    return redirect(url_for('home.load_teams'))