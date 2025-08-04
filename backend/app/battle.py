from flask import jsonify, render_template, Blueprint, request
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

        # Call the stored procedure 
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

@bp.route('/api/turn', methods=['POST'])
def process_turn():
    conn = None
    try:
        data = request.get_json()
        print("Received turn data:", data) # For debugging

        # --- Data from the frontend ---
        attacker_party = data.get('attacker_party')
        attacker_team_id = data.get('attacker_team_id')
        attacker_member_id = data.get('attacker_member_id')
        defender_party = data.get('defender_party')
        defender_team_id = data.get('defender_team_id')
        defender_member_id = data.get('defender_member_id')
        move_slot = data.get('move_slot')

        conn = getconn()
        cursor = conn.cursor()

        # The arguments must be in the exact order the procedure expects
        args = [
            attacker_party,
            attacker_team_id,
            attacker_member_id,
            defender_party,
            defender_team_id,
            defender_member_id,
            move_slot,
            '' # Placeholder for the OUT parameter
        ]
        
        # Execute the stored procedure
        cursor.callproc('process_battle_turn', args)
        
        # Fetch the value of the OUT parameter
        cursor.execute("SELECT @_process_battle_turn_7;") # The _7 corresponds to the 8th argument (index 7)
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        # After the turn, we need to get the new HP values to send back
        # This is a simplified query; a new SP could be more efficient
        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (data.get('player_team_id'), data.get('player_member_id')))
        player_hp = cursor.fetchone()['current_hp']

        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (data.get('opponent_team_id'), data.get('opponent_member_id')))
        opponent_hp = cursor.fetchone()['current_hp']

        conn.commit()

        return jsonify({
            "success": True,
            "message": outcome_message,
            "player_hp": player_hp,
            "opponent_hp": opponent_hp
        })

    except Exception as e:
        print(f"Error processing turn: {e}")
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
@bp.route('/api/ai-turn', methods=['POST'])
def process_ai_turn():
    conn = None
    try:
        data = request.get_json()
        user_team_id = data.get('player_team_id')
        user_member_id = data.get('player_member_id')
        gym_id = data.get('opponent_team_id')
        gym_member_id = data.get('opponent_member_id')

        conn = getconn()
        cursor = conn.cursor()

        # Step 1: Get data for the AI to make a decision
        # We need the AI's moves and the player's Pokémon's types.
        # This query is a bit complex; for a class project, a new SP for this would be impressive.
        ai_decision_query = """
            SELECT
                p_user.pType_1, p_user.pType_2,
                gtm.move_1_id, gtm.move_2_id, gtm.move_3_id, gtm.move_4_id,
                gtm.move_1_current_pp, gtm.move_2_current_pp, gtm.move_3_current_pp, gtm.move_4_current_pp
            FROM gym_leader_team_members gtm
            CROSS JOIN user_poke_team_members utm
            JOIN pokedex_entries p_user ON utm.pokedex_id = p_user.pokedex_id
            WHERE gtm.gym_id = %s AND gtm.gym_team_member_id = %s
            AND utm.user_team_id = %s AND utm.user_team_member_id = %s;
        """
        cursor.execute(ai_decision_query, (gym_id, gym_member_id, user_team_id, user_member_id))
        decision_data = cursor.fetchone()

# This is inside your process_ai_turn function in battle.py

        # Step 2: AI "Brain" - Score each available move
        best_move = {'slot': 0, 'score': -1}
        move_ids = [decision_data['move_1_id'], decision_data['move_2_id'], decision_data['move_3_id'], decision_data['move_4_id']]
        move_pps = [decision_data['move_1_current_pp'], decision_data['move_2_current_pp'], decision_data['move_3_current_pp'], decision_data['move_4_current_pp']]

        for i, move_id in enumerate(move_ids):
            if move_id is not None and move_pps[i] > 0:
                # Get move power and type
                cursor.execute("SELECT move_power, move_type FROM moves WHERE move_id = %s;", (move_id,))
                move_info = cursor.fetchone()
                
                # Get type effectiveness multiplier vs player's type 1
                cursor.execute("SELECT COALESCE(multiplier, 1.0) as mult FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], decision_data['pType_1']))
                multiplier = cursor.fetchone()['mult']
                
                # --- ADD THIS BLOCK TO CHECK THE SECOND TYPE ---
                if decision_data['pType_2'] is not None:
                    cursor.execute("SELECT COALESCE(multiplier, 1.0) as mult FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], decision_data['pType_2']))
                    multiplier *= cursor.fetchone()['mult']
                # --- END OF ADDED BLOCK ---
                
                score = move_info['move_power'] * multiplier
                if score > best_move['score']:
                    best_move['score'] = score
                    best_move['slot'] = i + 1

        # Step 3: Call the main procedure with the AI's chosen move
        args = ['GYM', gym_id, gym_member_id, 'USER', user_team_id, user_member_id, best_move['slot'], '']
        cursor.callproc('process_battle_turn', args)
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        # Get updated HP values to send back
        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (user_team_id, user_member_id))
        player_hp = cursor.fetchone()['current_hp']
        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (gym_id, gym_member_id))
        opponent_hp = cursor.fetchone()['current_hp']
        
        conn.commit()

        return jsonify({"success": True, "message": outcome_message, "player_hp": player_hp, "opponent_hp": opponent_hp})
    
    except Exception as e:
        print(f"Error in AI turn: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()