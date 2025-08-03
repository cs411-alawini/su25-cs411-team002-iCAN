from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn


# Routes will go here e.g. @bp.route('/auth')
bp = Blueprint('teams', __name__, url_prefix='/teams', template_folder='templates')

# Create the endpoint at url_prefix='/teams'
@bp.route('/create', methods=['GET', 'POST'])
def create_team():
    """
    Show the create team page, and handle Pokémon search.
    """
    team = session.get('team', [])
    user_team_id = session.get('user_team_id')
    user_id = session.get('user_id')

    

    team_name = ''
    if user_team_id and user_id:
        db_conn = getconn()
        try:
            with db_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT team_name FROM user_teams WHERE user_team_id = %s AND user_id = %s",
                    (user_team_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    team_name = row['team_name']
                    print(f"current team name is {team_name}")
                else:
                    team_name = ''
        finally:
            db_conn.close()

    if request.method == 'POST':
        # Get the search term from the form
        pokemon_input = request.form.get('pokemon_search', '').strip()

        results = []
        if pokemon_input:
            db_conn = getconn()
            try:
                with db_conn.cursor() as cursor:
                    query = """
                        SELECT name 
                        FROM pokedex_entries 
                        WHERE LOWER(name) LIKE %s
                        LIMIT 10;
                    """
                    cursor.execute(query, (f"%{pokemon_input.lower()}%",))
                    results = cursor.fetchall()
            finally:
                db_conn.close()

        return render_template('create_team.html', pokemon_results=results, team=team, team_name=team_name)

    # GET request, just render template with current team and no search results
    return render_template('create_team.html', team=team, team_name=team_name)



@bp.route('/add', methods=['POST'])
def add_pokemon():
    pokemon = request.form.get('add_pokemon')
    if pokemon:
        team = session.get('team', [])
        if len(team) < 6 and pokemon not in team:
            team.append(pokemon)
            session['team'] = team
    return redirect(url_for('teams.create_team'))


@bp.route('/update', methods=['POST'])
def update_team():
    user_team_id = session.get('user_team_id')
    if not user_team_id:
        # No team id saved, redirect or error
        return redirect(url_for('teams.create_team'))

    # Extract Pokémon names from form
    new_team_pokemon = []
    for i in range(6):
        poke_name = request.form.get(f'pokemon{i}', '').strip()
        if poke_name:
            new_team_pokemon.append(poke_name)

    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            # 1) Delete existing team members for this user_team_id
            delete_query = "DELETE FROM user_poke_team_members WHERE user_team_id = %s;"
            cursor.execute(delete_query, (user_team_id,))

            # 2) For each Pokémon, find its pokedex_id, then insert into user_poke_team_members
            select_pokedex_query = "SELECT pokedex_id FROM pokedex_entries WHERE LOWER(name) = %s LIMIT 1;"
            insert_member_query = """
                INSERT INTO user_poke_team_members (user_team_id, user_team_member_id, pokedex_id)
                VALUES (%s, %s, %s);
            """

            for idx, poke_name in enumerate(new_team_pokemon):
                cursor.execute(select_pokedex_query, (poke_name.lower(),))
                res = cursor.fetchone()
                if res:
                    pokedex_id = res['pokedex_id']
                    # Use idx+1 or some logic for user_team_member_id
                    user_team_member_id = idx + 1
                    cursor.execute(insert_member_query, (user_team_id, user_team_member_id, pokedex_id))
            db_conn.commit()

            print("We saved the team")
    finally:
        db_conn.close()

    # Optionally update session['team'] for UI
    session['team'] = new_team_pokemon

    return redirect(url_for('teams.create_team'))



@bp.route('/save-name', methods=['POST', 'GET'])
def save_team_name():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    db_conn = getconn()
    try:
        with db_conn.cursor() as cursor:
            user_team_id = session.get('user_team_id')

            if request.method == 'POST':
                team_name = request.form.get('team_name', '').strip()
                session['team_name'] = team_name

                if user_team_id:
                    # Update existing team name
                    update_query = """
                        UPDATE user_teams
                        SET team_name = %s
                        WHERE user_team_id = %s AND user_id = %s
                    """
                    cursor.execute(update_query, (team_name, user_team_id, user_id))
                else:
                    # Insert new team
                    insert_query = """
                        INSERT INTO user_teams (user_id, team_name, is_active)
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_query, (user_id, team_name, 1))
                    user_team_id = cursor.lastrowid
                    session['user_team_id'] = user_team_id

                db_conn.commit()
                return redirect(url_for('teams.create_team'))

            else:
                # GET request: load existing team name to pre-fill form if editing
                if user_team_id:
                    select_query = "SELECT team_name FROM user_teams WHERE user_team_id = %s AND user_id = %s"
                    cursor.execute(select_query, (user_team_id, user_id))
                    row = cursor.fetchone()
                    team_name = row[0] if row else ''
                else:
                    team_name = ''

    finally:
        db_conn.close()

    return render_template('save_team_name.html', team_name=team_name)

