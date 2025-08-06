from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn
import traceback

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

        # Get user's team id
        get_team_id = """
            SELECT user_team_id 
            FROM user_teams 
            WHERE user_id = %s AND is_active = TRUE;
        """
        cursor.execute(get_team_id, (user_id,))
        battle_team = cursor.fetchone()

        if not battle_team:
            return "You do not have an active team selected.", 400

        user_team_id = battle_team['user_team_id']

        # Before each battle, reset each pokemon's HP
        reset_hp = """
            UPDATE user_poke_team_members utm
            JOIN pokedex_entries p ON utm.pokedex_id = p.pokedex_id
            SET utm.current_hp = p.hp
            WHERE utm.user_team_id = %s;
        """
        cursor.execute(reset_hp, (user_team_id,))

        # Before each battle, reset each pokemon's move PP
        reset_pp = """
            UPDATE user_poke_team_members utm
            SET
                move_1_current_pp = (SELECT pp FROM moves WHERE move_id = utm.move_1_id),
                move_2_current_pp = (SELECT pp FROM moves WHERE move_id = utm.move_2_id),
                move_3_current_pp = (SELECT pp FROM moves WHERE move_id = utm.move_3_id),
                move_4_current_pp = (SELECT pp FROM moves WHERE move_id = utm.move_4_id)
            WHERE utm.user_team_id = %s;
        """
        cursor.execute(reset_pp, (user_team_id,))

        # Reset opponent's HP
        reset_opponent_hp = """
            UPDATE gym_leader_team_members glm
            JOIN pokedex_entries p ON glm.pokedex_id = p.pokedex_id
            SET glm.current_hp = p.hp
            WHERE glm.gym_id = %s;
        """
        cursor.execute(reset_opponent_hp, (gym_id,))

        # Reset opponent's move PP
        reset_opponent_pp = """
            UPDATE gym_leader_team_members glm
            SET
                move_1_current_pp = (SELECT pp FROM moves WHERE move_id = glm.move_1_id),
                move_2_current_pp = (SELECT pp FROM moves WHERE move_id = glm.move_2_id),
                move_3_current_pp = (SELECT pp FROM moves WHERE move_id = glm.move_3_id),
                move_4_current_pp = (SELECT pp FROM moves WHERE move_id = glm.move_4_id)
            WHERE glm.gym_id = %s;
        """
        cursor.execute(reset_opponent_pp, (gym_id,))
        conn.commit()
 
        # Call the stored procedure to get the battle state
        # Made by Tanjie
        cursor.callproc('get_battle_state', (user_team_id, gym_id))
        results = cursor.fetchall()

        print(f"results = {results}")
        battle_state = {}
        for row in results:
            if row['party_type'] == 'USER':
                battle_state['player_pokemon'] = row
            else:
                battle_state['opponent_pokemon'] = row

        # Keep track of pokemon's max hp for UI accuracy
        for key in ['player_pokemon', 'opponent_pokemon']:
            if key in battle_state:
                battle_state[key]['hp'] = battle_state[key].get('max_hp', 1)

        opponent_max_hp = battle_state['opponent_pokemon']['hp']

        for party in battle_state.values():
            party['moves'] = [
                {'move_name': party['move_1_name'], 'current_pp': party['move_1_current_pp'], 'max_pp': party['move_1_max_pp']},
                {'move_name': party['move_2_name'], 'current_pp': party['move_2_current_pp'], 'max_pp': party['move_2_max_pp']},
                {'move_name': party['move_3_name'], 'current_pp': party['move_3_current_pp'], 'max_pp': party['move_3_max_pp']},
                {'move_name': party['move_4_name'], 'current_pp': party['move_4_current_pp'], 'max_pp': party['move_4_max_pp']}
            ]

        return render_template('battle.html', state=battle_state, opponent_max_hp=opponent_max_hp)

    except Exception as e:
        print(f"Error starting battle: {e}")
        return "An error occurred in start_battle()", 500
    finally:
        if conn:
            conn.close()


@bp.route('/api/team/<int:user_team_id>', methods=['GET'])
def get_user_team(user_team_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        # Get the user's battle team information
        get_battle_team_info = """
            SELECT utm.user_team_member_id, p.name, utm.current_hp,
                p.hp AS max_hp, p.image_url
            FROM user_poke_team_members utm
            JOIN pokedex_entries p ON utm.pokedex_id = p.pokedex_id
            WHERE utm.user_team_id = %s
            ORDER BY utm.user_team_member_id;
        """
        cursor.execute(get_battle_team_info, (user_team_id,))
        battle_team_info_results = cursor.fetchall()
        return jsonify(battle_team_info_results)

    except Exception as e:
        print(f"Error fetching team data in get_user_team(): {e}")
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

        # Call the stored procedure to process the battle turn
        # Made by Tanjie
        sp_args = [
            attacker_party, attacker_team_id, attacker_member_id,
            defender_party, defender_team_id, defender_member_id,
            move_slot, ''
        ]
        
        cursor.callproc('process_battle_turn', sp_args)
        
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        # Get current HP for currently fighting pokemon
        get_current_pokemon_hp = """
            SELECT current_hp, pokedex_id
            FROM user_poke_team_members
            WHERE user_team_id = %s AND user_team_member_id = %s;
        """
        cursor.execute(get_current_pokemon_hp, (data.get('player_team_id'), data.get('player_member_id')))
        player_record = cursor.fetchone()
        player_hp = player_record['current_hp']
        player_pokedex_id = player_record['pokedex_id']

        # Get current HP for gym (opponent) pokemon
        get_gym_pokemon_hp = """
            SELECT current_hp, pokedex_id
            FROM gym_leader_team_members
            WHERE gym_id = %s AND gym_team_member_id = %s;
        """
        cursor.execute(get_gym_pokemon_hp, (data.get('opponent_team_id'), data.get('opponent_member_id')))
        gym_leader_record = cursor.fetchone()
        opponent_hp = gym_leader_record['current_hp']
        opponent_pokedex_id = gym_leader_record['pokedex_id']

        # Get max HP for current player's pokemon
        get_max_hp = """
            SELECT hp AS max_hp 
            FROM pokedex_entries 
            WHERE pokedex_id = %s;
        """
        cursor.execute(get_max_hp, (player_pokedex_id,))
        player_max_hp = cursor.fetchone()['max_hp']

        # Get max HP for current gym leader's pokemon
        get_max_gym_hp = """
            SELECT hp AS max_hp 
            FROM pokedex_entries 
            WHERE pokedex_id = %s;
        """
        cursor.execute(get_max_gym_hp, (opponent_pokedex_id,))
        opponent_max_hp = cursor.fetchone()['max_hp']

        # Get PP for current player's pokemon
        get_player_pp = """
            SELECT move_1_current_pp, move_2_current_pp, move_3_current_pp, move_4_current_pp
            FROM user_poke_team_members
            WHERE user_team_id = %s AND user_team_member_id = %s;
        """
        cursor.execute(get_player_pp, (data.get('player_team_id'), data.get('player_member_id')))
        move_pps_row = cursor.fetchone()
        player_move_pps = {
            'move_1_current_pp': move_pps_row['move_1_current_pp'],
            'move_2_current_pp': move_pps_row['move_2_current_pp'],
            'move_3_current_pp': move_pps_row['move_3_current_pp'],
            'move_4_current_pp': move_pps_row['move_4_current_pp'],
        }

        # For when gym team leaders' pokemon gaints
        if opponent_hp <= 0:
            get_all_gym_pokemon = """
                SELECT *
                FROM gym_leader_team_members g
                JOIN pokedex_entries p ON g.pokedex_id = p.pokedex_id
                WHERE g.gym_id = %s AND g.current_hp > 0
                ORDER BY g.gym_team_member_id ASC
            """
            cursor.execute(get_all_gym_pokemon, (data.get('opponent_team_id'),))
            available_pokemon = cursor.fetchall()

            if available_pokemon:
                new_opponent = available_pokemon[0]
                return jsonify({
                    "success": True,
                    "message": outcome_message + f" {new_opponent['name']} was sent out!",
                    "player_hp": player_hp,
                    "player_max_hp": player_max_hp,
                    "opponent_hp": new_opponent['current_hp'],
                    "opponent_max_hp": new_opponent['hp'],
                    "player_move_pps": player_move_pps, 
                    "ai_switch_info": {
                        "name": new_opponent['name'],
                        "image_url": new_opponent['image_url'],
                        "current_hp": new_opponent['current_hp'],
                        "max_hp": new_opponent['hp'],
                        "gym_team_member_id": new_opponent['gym_team_member_id']
                    }
                })
            else:
                return jsonify({
                    "success": True,
                    "message": outcome_message + " All of the opponent's Pokémon have fainted. You win!",
                    "player_hp": player_hp,
                    "player_max_hp": player_max_hp,
                    "opponent_hp": 0,
                    "opponent_max_hp": 0,
                    "player_move_pps": player_move_pps,
                    "ai_switch_info": {
                        "game_over": True
                    }
                }) 

        conn.commit()

        # Turn results
        return jsonify({
            "success": True,
            "message": outcome_message,
            "player_hp": player_hp,
            "player_max_hp": player_max_hp,
            "opponent_hp": opponent_hp,
            "opponent_max_hp": opponent_max_hp,
            "player_move_pps": player_move_pps  
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

        print("DEBUG: we got here 1")
        get_gym_moves_and_pp = """
            SELECT name, move_1_id, move_2_id, move_3_id, move_4_id,
                   move_1_current_pp, move_2_current_pp, move_3_current_pp, move_4_current_pp
            FROM gym_leader_team_members
            JOIN pokedex_entries ON gym_leader_team_members.pokedex_id = pokedex_entries.pokedex_id
            WHERE gym_id = %s AND gym_team_member_id = %s;
        """
        cursor.execute(get_gym_moves_and_pp, (gym_id, gym_member_id))
        gym_data = cursor.fetchone()

        print("DEBUG; we got here 2")
        get_player_moves_and_pp = """
            SELECT pType_1, pType_2
            FROM user_poke_team_members
            JOIN pokedex_entries ON user_poke_team_members.pokedex_id = pokedex_entries.pokedex_id
            WHERE user_team_id = %s AND user_team_member_id = %s;
        """
        cursor.execute(get_player_moves_and_pp, (user_team_id, user_member_id))
        player_data = cursor.fetchone()
        
        if not gym_data or not player_data:
            return jsonify({"success": False, "message": "AI failed to gather battle data."}), 500
        
        best_move = {'slot': 0, 'score': -1}
        move_ids = [gym_data['move_1_id'], gym_data['move_2_id'], gym_data['move_3_id'], gym_data['move_4_id']]
        move_pps = [gym_data['move_1_current_pp'], gym_data['move_2_current_pp'], gym_data['move_3_current_pp'], gym_data['move_4_current_pp']]

        for i, move_id in enumerate(move_ids):
            if move_id is not None and move_pps[i] > 0:
                print(f"DEBUG; we got here 3 where move_id = {move_id}")
                cursor.execute("SELECT move_power, move_type FROM moves WHERE move_id = %s;", (move_id,))
                move_info = cursor.fetchone()
                
                print(f" move type is {move_info['move_type']} and ptype1 is {player_data['pType_1']}")
                cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_1']))
                result1 = cursor.fetchone()
                multiplier = result1['multiplier'] if result1 else 1.0

                if player_data['pType_2'] is not None:
                    print(f"move type is {move_info['move_type']} and ptype2 is {player_data['pType_2']}")
                    cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_2']))
                    result2 = cursor.fetchone()
                    if result2:
                        multiplier *= result2['multiplier']
                
                score = move_info['move_power'] * multiplier
                if score > best_move['score']:
                    best_move['score'] = score
                    best_move['slot'] = i + 1
        
        if best_move['slot'] == 0:
            for i, pp in enumerate(move_pps):
                if move_ids[i] is not None and pp > 0:
                    best_move['slot'] = i + 1
                    break

        # Call the stored procedure Tanjie made
        sp_args = ['GYM', gym_id, gym_member_id, 'USER', user_team_id, user_member_id, best_move['slot'], '']
        cursor.callproc('process_battle_turn', sp_args)

        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (user_team_id, user_member_id))
        player_hp = cursor.fetchone()['current_hp']

        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (gym_id, gym_member_id))
        opponent_hp = cursor.fetchone()['current_hp']
        

        if player_hp <= 0:
            get_remaining_pokemon = """
                SELECT *
                FROM user_poke_team_members u
                JOIN pokedex_entries p ON u.pokedex_id = p.pokedex_id
                WHERE u.user_team_id = %s AND u.current_hp > 0
                ORDER BY u.user_team_member_id ASC
            """
            cursor.execute(get_remaining_pokemon, (user_team_id,))
            remaining_pokemon = cursor.fetchall()

            if remaining_pokemon:
                return jsonify({
                    "success": True,
                    "message": outcome_message + f" Your {remaining_pokemon[0]['name']} is ready to go!",
                    "player_hp": 0,
                    "opponent_hp": opponent_hp,
                    "force_player_switch": {
                        "name": remaining_pokemon[0]['name'],
                        "image_url": remaining_pokemon[0]['image_url'],
                        "current_hp": remaining_pokemon[0]['current_hp'],
                        "max_hp": remaining_pokemon[0]['hp'],
                        "user_team_member_id": remaining_pokemon[0]['user_team_member_id']
                    }
                })
            else:
                return jsonify({
                    "success": True,
                    "message": outcome_message + " All your Pokémon have fainted. You lose!",
                    "player_hp": 0,
                    "opponent_hp": opponent_hp,
                    "game_over": True
                })

        conn.commit()
        return jsonify({ "success": True, "message": outcome_message, "player_hp": player_hp, "opponent_hp": opponent_hp })
    
    except Exception as e:
        print(f"Error in AI turn in process_AI_turn(): {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/api/moves/<int:member_id>')
def get_moves(member_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()  

        get_poke_moves = """
            SELECT 
                move_1_id, move_1_current_pp,
                move_2_id, move_2_current_pp,
                move_3_id, move_3_current_pp,
                move_4_id, move_4_current_pp
            FROM user_poke_team_members
            WHERE user_team_member_id = %s;
        """

        cursor.execute(get_poke_moves, (member_id,))
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": "No data found"}), 404

        move_ids = [
            record['move_1_id'],
            record['move_2_id'],
            record['move_3_id'],
            record['move_4_id']
        ]
        current_pps = [
            record['move_1_current_pp'],
            record['move_2_current_pp'],
            record['move_3_current_pp'],
            record['move_4_current_pp']
        ]


        moves = []
        for i in range(4):
            if move_ids[i] is None:
                continue

            cursor.execute("SELECT move_name, pp FROM moves WHERE move_id = %s", (move_ids[i],))
            move_row = cursor.fetchone()
            if not move_row:
                move_name = "Unknown Move"
                max_pp = 0
            else:
                move_name = move_row['move_name']
                max_pp = move_row['pp']

            moves.append({
                "move_name": move_name,
                "current_pp": current_pps[i],
                "max_pp": max_pp
            })


        print(f"Fetching moves for user_team_member_id={member_id}")
        print("Move IDs:", move_ids)
        for move_id in move_ids:
            if move_id is not None:
                cursor.execute("SELECT move_name, pp FROM moves WHERE move_id = %s", (move_id,))
                move_info = cursor.fetchone()
                print(f"Move info for ID {move_id}: {move_info}")

        return jsonify(moves)

    except Exception as e:
        print(f"[EXCEPTION in get_moves] member_id={member_id}, error={e}")
        traceback.print_exc()
        return jsonify({"error": "Move fetch failed"}), 500
    finally:
        if conn:
            conn.close()
