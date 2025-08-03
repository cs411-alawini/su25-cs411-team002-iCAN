from flask import jsonify, render_template, Blueprint
from app.db import getconn

# Routes will go here e.g. @bp.route('/battle')
bp = Blueprint('battle', __name__, url_prefix='/battle')

# Route for starting a battle 
# Create the endpoint at url_prefix='/battle/start/<gym_id>'
@bp.route('/start/<int:gym_id>')
def start_battle(gym_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        # TODO: Preset user_id for debugging until user auth is connected
        user_id = 1

        query = "SELECT user_team_id FROM user_teams WHERE user_id = %s AND is_active = TRUE;"
        # Find the user's active team ID
        cursor.execute(query, (user_id))
        active_team = cursor.fetchone()

        if not active_team:
            # Handle case where the user has no active team
            return "You do not have an active team selected.", 400

        user_team_id = active_team['user_team_id']

        # Step 3: Call the stored procedure 
        cursor.callproc('get_battle_state', (user_team_id, gym_id))
        results = cursor.fetchall()
        conn.commit()

        # Process the results to fit the template's expected structure
        battle_state = {}
        for row in results:
            print(row)
            if row['party_type'] == 'USER':
                battle_state['player_pokemon'] = row
            else:
                battle_state['opponent_pokemon'] = row
        
        # Structure the moves into a list for the template
        for party in battle_state.values():
            party['moves'] = [
                {'move_name': party['move_1_name'], 'current_pp': party['move_1_current_pp'], 'max_pp': party['move_1_max_pp']},
                {'move_name': party['move_2_name'], 'current_pp': party['move_2_current_pp'], 'max_pp': party['move_2_max_pp']},
                {'move_name': party['move_3_name'], 'current_pp': party['move_3_current_pp'], 'max_pp': party['move_3_max_pp']},
                {'move_name': party['move_4_name'], 'current_pp': party['move_4_current_pp'], 'max_pp': party['move_4_max_pp']}
            ]

        return render_template('battle.html', state=battle_state)

    except Exception as e:
        print(f"Error starting battle: {e}")
        return "An error occurred.", 500
    finally:
        if conn:
            conn.close()

# Route for getting a user's team during battle
@bp.route('/api/team/<int:user_team_id>', methods=['GET'])
def get_user_team(user_team_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        # Query to get all members of a user team 
        query = """
            SELECT
                utm.user_team_member_id,
                p.name,
                utm.current_hp,
                p.hp AS max_hp,
                p.image_url
            FROM
                user_poke_team_members utm
            JOIN
                pokedex_entries p
            ON
                utm.pokedex_id = p.pokedex_id
            WHERE
                utm.user_team_id = %s
            ORDER BY
                utm.user_team_member_id;
        """
        cursor.execute(query, (user_team_id,))
        team_data = cursor.fetchall()

        return jsonify(team_data)

    except Exception as e:
        print(f"Error fetching team data: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
