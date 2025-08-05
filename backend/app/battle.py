from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn

bp = Blueprint('battle', __name__, url_prefix='/battle')

@bp.route('/start/<int:gym_id>')
def start_battle(gym_id):
    conn = None
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        user_id = session['user_id']

        conn = getconn()
        cursor = conn.cursor()

        query = "SELECT user_team_id FROM user_teams WHERE user_id = %s AND is_active = TRUE;"
        cursor.execute(query, (user_id,))
        active_team = cursor.fetchone()

        if not active_team:
            return "You do not have an active team selected.", 400

        user_team_id = active_team['user_team_id']

        cursor.callproc('get_battle_state', (user_team_id, gym_id))
        results = cursor.fetchall()
        conn.commit()

        battle_state = {}
        for row in results:
            if row['party_type'] == 'USER':
                battle_state['player_pokemon'] = row
            else:
                battle_state['opponent_pokemon'] = row
        
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

@bp.route('/api/team/<int:user_team_id>', methods=['GET'])
def get_user_team(user_team_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        query = """
            SELECT
                utm.user_team_member_id, p.name, utm.current_hp,
                p.hp AS max_hp, p.image_url
            FROM user_poke_team_members utm
            JOIN pokedex_entries p ON utm.pokedex_id = p.pokedex_id
            WHERE utm.user_team_id = %s
            ORDER BY utm.user_team_member_id;
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
        
        attacker_party = data.get('attacker_party')
        attacker_team_id = data.get('attacker_team_id')
        attacker_member_id = data.get('attacker_member_id')
        defender_party = data.get('defender_party')
        defender_team_id = data.get('defender_team_id')
        defender_member_id = data.get('defender_member_id')
        move_slot = data.get('move_slot')

        conn = getconn()
        cursor = conn.cursor()

        args = [
            attacker_party, attacker_team_id, attacker_member_id,
            defender_party, defender_team_id, defender_member_id,
            move_slot, ''
        ]
        
        cursor.callproc('process_battle_turn', args)
        
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (data.get('player_team_id'), data.get('player_member_id')))
        player_hp = cursor.fetchone()['current_hp']

        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (data.get('opponent_team_id'), data.get('opponent_member_id')))
        opponent_hp = cursor.fetchone()['current_hp']

        conn.commit()

        return jsonify({
            "success": True, "message": outcome_message,
            "player_hp": player_hp, "opponent_hp": opponent_hp
        })

    except Exception as e:
        print(f"Error processing turn: {e}")
        if conn: conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn: conn.close()

# This is the updated process_ai_turn function with debug messages

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

        # --- ADD DEBUG PRINTS BEFORE EACH QUERY ---

        print("--- AI DEBUG: RUNNING QUERY A (GET AI DATA) ---")
        cursor.execute("""
            SELECT name, move_1_id, move_2_id, move_3_id, move_4_id,
                   move_1_current_pp, move_2_current_pp, move_3_current_pp, move_4_current_pp
            FROM gym_leader_team_members
            JOIN pokedex_entries ON gym_leader_team_members.pokedex_id = pokedex_entries.pokedex_id
            WHERE gym_id = %s AND gym_team_member_id = %s;
        """, (gym_id, gym_member_id))
        ai_data = cursor.fetchone()

        print("--- AI DEBUG: RUNNING QUERY B (GET PLAYER DATA) ---")
        cursor.execute("""
            SELECT pType_1, pType_2
            FROM user_poke_team_members
            JOIN pokedex_entries ON user_poke_team_members.pokedex_id = pokedex_entries.pokedex_id
            WHERE user_team_id = %s AND user_team_member_id = %s;
        """, (user_team_id, user_member_id))
        player_data = cursor.fetchone()
        
        if not ai_data or not player_data:
            return jsonify({"success": False, "message": "AI failed to gather battle data."}), 500
        
        best_move = {'slot': 0, 'score': -1}
        move_ids = [ai_data['move_1_id'], ai_data['move_2_id'], ai_data['move_3_id'], ai_data['move_4_id']]
        move_pps = [ai_data['move_1_current_pp'], ai_data['move_2_current_pp'], ai_data['move_3_current_pp'], ai_data['move_4_current_pp']]

        for i, move_id in enumerate(move_ids):
            if move_id is not None and move_pps[i] > 0:
                print(f"--- AI DEBUG: GETTING MOVE INFO FOR MOVE_ID {move_id} ---")
                cursor.execute("SELECT move_power, move_type FROM moves WHERE move_id = %s;", (move_id,))
                move_info = cursor.fetchone()
                
                print(f"--- AI DEBUG: GETTING MULTIPLIER 1 FOR TYPE {move_info['move_type']} vs {player_data['pType_1']} ---")
                cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_1']))
                result1 = cursor.fetchone()
                multiplier = result1['multiplier'] if result1 else 1.0

                if player_data['pType_2'] is not None:
                    print(f"--- AI DEBUG: GETTING MULTIPLIER 2 FOR TYPE {move_info['move_type']} vs {player_data['pType_2']} ---")
                    cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_2']))
                    result2 = cursor.fetchone()
                    if result2:
                        multiplier *= result2['multiplier']
                
                score = move_info['move_power'] * multiplier
                if score > best_move['score']:
                    best_move['score'] = score
                    best_move['slot'] = i + 1
        
        # ... (rest of the function is the same)
        
        if best_move['slot'] == 0:
            for i, pp in enumerate(move_pps):
                if move_ids[i] is not None and pp > 0:
                    best_move['slot'] = i + 1
                    break

        print("--- AI DEBUG: CALLING STORED PROCEDURE ---")
        args = ['GYM', gym_id, gym_member_id, 'USER', user_team_id, user_member_id, best_move['slot'], '']
        cursor.callproc('process_battle_turn', args)

        print("--- AI DEBUG: FETCHING OUT PARAMETER ---")
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        print("--- AI DEBUG: FETCHING PLAYER HP ---")
        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (user_team_id, user_member_id))
        player_hp = cursor.fetchone()['current_hp']

        print("--- AI DEBUG: FETCHING OPPONENT HP ---")
        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (gym_id, gym_member_id))
        opponent_hp = cursor.fetchone()['current_hp']
        
        conn.commit()
        return jsonify({ "success": True, "message": outcome_message, "player_hp": player_hp, "opponent_hp": opponent_hp })
    
    except Exception as e:
        print(f"Error in AI turn: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()