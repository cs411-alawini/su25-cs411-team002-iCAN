from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn
import traceback

bp = Blueprint('battle', __name__, url_prefix='/battle')

@bp.route('/start/<int:gym_id>')
def start_battle(gym_id):
    """
    The user has pressed the gym leader they want to enter from the Gyms page, or they pressed
        the enter gym button on the homepage or profile page.
    """
    conn = None
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        # This should have been stored from auth.py
        user_id = session['user_id']

        # Connect to GCP
        conn = getconn()
        cursor = conn.cursor()

        # Get user's team to battle the gym with.
        # By default, this will be the first team they created.
        get_team_id = """
            SELECT user_team_id 
            FROM user_teams 
            WHERE user_id = %s AND is_active = TRUE;
        """
        cursor.execute(get_team_id, (user_id,))
        battle_team = cursor.fetchone()

        if not battle_team:
            return "You do not have an active team selected.", 400

        # Get the team's id from the query results
        user_team_id = battle_team['user_team_id']

        # Before each battle, reset each pokemon's HP by writing to DB
        # We know which value to reset to by looking at the pokedex (static DB)
        reset_hp = """
            UPDATE user_poke_team_members utm
            JOIN pokedex_entries p ON utm.pokedex_id = p.pokedex_id
            SET utm.current_hp = p.hp
            WHERE utm.user_team_id = %s;
        """
        cursor.execute(reset_hp, (user_team_id,))

        # Before each battle, reset each pokemon's move PP by writing to DB
        # We know which value to reset to by looking at the moves table (static DB)
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

        # Reset opponent's HP by writing to DB
        # We know which value to reset to by looking at the pokedex (static DB)
        reset_opponent_hp = """
            UPDATE gym_leader_team_members glm
            JOIN pokedex_entries p ON glm.pokedex_id = p.pokedex_id
            SET glm.current_hp = p.hp
            WHERE glm.gym_id = %s;
        """
        cursor.execute(reset_opponent_hp, (gym_id,))

        # Reset opponent's move PP by writing to DB
        # We know which value to reset to by looking at the moves table (static DB)
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
 
        # Call Tanjie's stored procedure to get the battle state
        # STORED PROCEDURE --> get_battle_state(userTeamId, gymId)
        # 1) This heals the user's and opponent's team to full HP
        # 2) Get initial battle state for user: current hp, max hp, current pp, max pp for moves
        # 3) Get initial battle state for gym leader: current hp, max hp, current pp, max pp for moves
        cursor.callproc('get_battle_state', (user_team_id, gym_id))
        results = cursor.fetchall()

        # DEBUGGING
        # print(f"results = {results}")

        # Get user and opponent's team information from query results
        # Create a dictionary with player and opponnet as keys
        battle_state = {}
        for record in results:
            # Get user information
            if record['party_type'] == 'USER':
                battle_state['player_pokemon'] = record
            # Get gym leader information
            else:
                battle_state['opponent_pokemon'] = record

        # Create a key to hold the pokemon's max hp for both the user and opponent
        for key in ['player_pokemon', 'opponent_pokemon']:
            if key in battle_state:
                battle_state[key]['hp'] = battle_state[key].get('max_hp', 1)

        # Grab the gym leaders' pokemon's max hp from the battle_state dictionary
        opponent_max_hp = battle_state['opponent_pokemon']['hp']

        # Get the moves of each pokemon for the user and opponent
        for party in battle_state.values():
            party['moves'] = [
                {'move_name': party['move_1_name'], 'current_pp': party['move_1_current_pp'], 'max_pp': party['move_1_max_pp']},
                {'move_name': party['move_2_name'], 'current_pp': party['move_2_current_pp'], 'max_pp': party['move_2_max_pp']},
                {'move_name': party['move_3_name'], 'current_pp': party['move_3_current_pp'], 'max_pp': party['move_3_max_pp']},
                {'move_name': party['move_4_name'], 'current_pp': party['move_4_current_pp'], 'max_pp': party['move_4_max_pp']}
            ]

        # Dictionary battle_state now contains:
        # 1) User: team_id, member_id, pokemon name, current hp, max hp, moves, and move pp
        # 2) Opponent: team_id, member_id, pokemon name, current hp, max hp, moves, and move pp
        # 3) 'hp' KEY for user and opponent for each pokemon
        # 4) 'moves' KEY for user and opponent for each pokemon
        # Send the dictionary of information to Jinja and the opponent pokemon's max hp
        return render_template('battle.html', state=battle_state, opponent_max_hp=opponent_max_hp)

    except Exception as e:
        print(f"Error starting battle: {e}")
        return "An error occurred in start_battle()", 500
    finally:
        if conn:
            conn.close()



@bp.route('/api/team/<int:user_team_id>', methods=['GET'])
def get_user_team(user_team_id):
    """
    Get the user's first team. Use this team for the user during
        battle. Also, ensure that a user has at least one team.
    """
    conn = None
    try:
        # Open GCP and cursor for SQL queries
        conn = getconn()
        cursor = conn.cursor()

        # Get the user's first team
        # This is the team that will be used during battle
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
        
        # Send this information to JS in battle.html for showMoveMenu()
        return jsonify(battle_team_info_results)

    except Exception as e:
        print(f"Error fetching team data in get_user_team(): {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/api/turn', methods=['POST'])
def process_turn():
    """
    A player has made a move with their pokemon. Process
        the damage, hp, and other important information for the game.
        This will determine the UI of the game and the actual gameplay
        itself.
    We will handle the opponent's move in another function.
    """
    conn = None
    try:
        # Get JSON data from handleMoveClick(moveSlot)
        data = request.get_json()
        
        # Extract JSON data into variables to use
        attacker_party = data.get('attacker_party')
        attacker_team_id = data.get('attacker_team_id')
        attacker_member_id = data.get('attacker_member_id')
        defender_party = data.get('defender_party')
        defender_team_id = data.get('defender_team_id')
        defender_member_id = data.get('defender_member_id')
        move_slot = data.get('move_slot')

        # Connect to GCP and open cursor for queries
        conn = getconn()
        cursor = conn.cursor()

        # Call the stored procedure to process the battle turn
        # STORED PROCEDURE --> process_battle_turn(args1, ..., args7)
        sp_args = [
            attacker_party, attacker_team_id, attacker_member_id,
            defender_party, defender_team_id, defender_member_id,
            move_slot, ''
        ] 
        cursor.callproc('process_battle_turn', sp_args)
        
        # Get "[Pokemon] used [move]!" message from the stored procedure"
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        # Get current HP and pokedex_id for currently fighting pokemon
        get_current_pokemon_hp = """
            SELECT current_hp, pokedex_id
            FROM user_poke_team_members
            WHERE user_team_id = %s AND user_team_member_id = %s;
        """
        cursor.execute(get_current_pokemon_hp, (data.get('player_team_id'), data.get('player_member_id')))
        player_record = cursor.fetchone()
        player_hp = player_record['current_hp']
        player_pokedex_id = player_record['pokedex_id']

        # Get current HP and pokedex_id for current gym (opponent) pokemon
        get_gym_pokemon_hp = """
            SELECT current_hp, pokedex_id
            FROM gym_leader_team_members
            WHERE gym_id = %s AND gym_team_member_id = %s;
        """
        cursor.execute(get_gym_pokemon_hp, (data.get('opponent_team_id'), data.get('opponent_member_id')))
        gym_leader_record = cursor.fetchone()
        opponent_hp = gym_leader_record['current_hp']
        opponent_pokedex_id = gym_leader_record['pokedex_id']

        # Get max HP for current player's pokemon from pokedex (static)
        get_max_hp = """
            SELECT hp AS max_hp 
            FROM pokedex_entries 
            WHERE pokedex_id = %s;
        """
        cursor.execute(get_max_hp, (player_pokedex_id,))
        player_max_hp = cursor.fetchone()['max_hp']

        # Get max HP for current gym leader's pokemon from pokedex (static)
        get_max_gym_hp = """
            SELECT hp AS max_hp 
            FROM pokedex_entries 
            WHERE pokedex_id = %s;
        """
        cursor.execute(get_max_gym_hp, (opponent_pokedex_id,))
        opponent_max_hp = cursor.fetchone()['max_hp']

        # Get PP for all four moves of the user's current pokemon
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

        # Check to see if the gym leaders' pokemon has fainted
        if opponent_hp <= 0:
            # Find the next available pokemon on the gym leader's team that can fight
            get_all_gym_pokemon = """
                SELECT *
                FROM gym_leader_team_members g
                JOIN pokedex_entries p ON g.pokedex_id = p.pokedex_id
                WHERE g.gym_id = %s AND g.current_hp > 0
                ORDER BY g.gym_team_member_id ASC
            """
            cursor.execute(get_all_gym_pokemon, (data.get('opponent_team_id'),))
            available_pokemon = cursor.fetchall()

            # If the gym leader still has healthy pokemon on its team, switch
            # to the next pokemon on the team, via team_member_id
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
                # The gym leader has no more pokemon left to play, so..
                # The user wins!
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

        # Add changes to database
        conn.commit()

        # Return this game's turn results to handleMoveClick(moveSlot) in battle.html
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
    """
    Now that the user has played a turn, we will not handle the gym leader (opponent, or "ai")
        pokemon's moves and turns here.
    """
    conn = None
    try:
        # Get JSON information via triggerAITurn()
        data = request.get_json()
        user_team_id = data.get('player_team_id')
        user_member_id = data.get('player_member_id')
        gym_id = data.get('opponent_team_id')
        gym_member_id = data.get('opponent_member_id')

        # Connect to GCP and prepare to write SQL queries
        conn = getconn()
        cursor = conn.cursor()

        # DEBUGGING
        # print("DEBUG: we got here 1")

        # Get the gym leader pokemon's move information
        get_gym_moves_and_pp = """
            SELECT name, move_1_id, move_2_id, move_3_id, move_4_id,
                   move_1_current_pp, move_2_current_pp, move_3_current_pp, move_4_current_pp
            FROM gym_leader_team_members
            JOIN pokedex_entries ON gym_leader_team_members.pokedex_id = pokedex_entries.pokedex_id
            WHERE gym_id = %s AND gym_team_member_id = %s;
        """
        cursor.execute(get_gym_moves_and_pp, (gym_id, gym_member_id))
        gym_data = cursor.fetchone()

        # DEBUGGING
        # print("DEBUG; we got here 2")

        # Get the player/user's pokemon's pType information
        # This will be used in calculating the effectiveness/damage of 
        # the opponent's move
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
        
        # Choose the best move for the gym leader pokemon to make
        best_move = {'slot': 0, 'score': -1}
        move_ids = [gym_data['move_1_id'], gym_data['move_2_id'], gym_data['move_3_id'], gym_data['move_4_id']]
        move_pps = [gym_data['move_1_current_pp'], gym_data['move_2_current_pp'], gym_data['move_3_current_pp'], gym_data['move_4_current_pp']]

        # Look at each move for the pokemon, individually
        for i, move_id in enumerate(move_ids):
            if move_id is not None and move_pps[i] > 0:
                # DEBUGGING
                # print(f"DEBUG; we got here 3 where move_id = {move_id}")

                # Get this move's power and type
                cursor.execute("SELECT move_power, move_type FROM moves WHERE move_id = %s;", (move_id,))
                move_info = cursor.fetchone()
                
                # DEBUGGING
                # print(f" move type is {move_info['move_type']} and ptype1 is {player_data['pType_1']}")

                # Get the type matchup for the user's pokemon's pType 1 (first type)
                cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_1']))
                result1 = cursor.fetchone()
                multiplier = result1['multiplier'] if result1 else 1.0

                # Get the type matchup for the user's pokemon's pType 2 (second type)
                # Not all pokemon have a second pType
                if player_data['pType_2'] is not None:
                    # DEBUGGING
                    # print(f"move type is {move_info['move_type']} and ptype2 is {player_data['pType_2']}")

                    cursor.execute("SELECT multiplier FROM type_matchups WHERE attacking_type = %s AND defending_type = %s;", (move_info['move_type'], player_data['pType_2']))
                    result2 = cursor.fetchone()
                    if result2:
                        multiplier *= result2['multiplier']
                
                # Calculate the impact of the gym's pokemon against the user
                # Formula: power * type effectiveness
                score = move_info['move_power'] * multiplier
                if score > best_move['score']:
                    best_move['score'] = score
                    best_move['slot'] = i + 1
        
        # If no effective/best move was calculated
        if best_move['slot'] == 0:
            for i, pp in enumerate(move_pps):
                if move_ids[i] is not None and pp > 0:
                    best_move['slot'] = i + 1
                    break

        # Call the stored procedure Tanjie made to apply the best move of the gym to the user
        # STORED PROCEDURE --> process_battle_turn(args1, .., args7)
        sp_args = ['GYM', gym_id, gym_member_id, 'USER', user_team_id, user_member_id, best_move['slot'], '']
        cursor.callproc('process_battle_turn', sp_args)

        # Get outcome message from stored procedure
        cursor.execute("SELECT @_process_battle_turn_7;")
        result = cursor.fetchone()
        outcome_message = result.get('@_process_battle_turn_7')

        # Get the updated HP for gym and user pokemon
        cursor.execute("SELECT current_hp FROM user_poke_team_members WHERE user_team_id = %s AND user_team_member_id = %s;", (user_team_id, user_member_id))
        player_hp = cursor.fetchone()['current_hp']

        cursor.execute("SELECT current_hp FROM gym_leader_team_members WHERE gym_id = %s AND gym_team_member_id = %s;", (gym_id, gym_member_id))
        opponent_hp = cursor.fetchone()['current_hp']
        

        # Determine if player's pokemon fainted
        if player_hp <= 0:
            # Look to see if player has other available pokemon left to fight
            get_remaining_pokemon = """
                SELECT *
                FROM user_poke_team_members u
                JOIN pokedex_entries p ON u.pokedex_id = p.pokedex_id
                WHERE u.user_team_id = %s AND u.current_hp > 0
                ORDER BY u.user_team_member_id ASC
            """
            cursor.execute(get_remaining_pokemon, (user_team_id,))
            remaining_pokemon = cursor.fetchall()

            # Force the user to switch pokemon
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
                # The user has no more pokemon to play
                # The user has lost ):
                return jsonify({
                    "success": True,
                    "message": outcome_message + " All your Pokémon have fainted. You lose!",
                    "player_hp": 0,
                    "opponent_hp": opponent_hp,
                    "game_over": True
                })

        # Commit changes to database
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
    """
    Get information about the current user's pokemon's moves.
    """
    conn = None
    try:
        # Connect to GCP and get ready to write SQL queries
        conn = getconn()
        cursor = conn.cursor()  

        # Get the moves and pp for the current user's pokemon
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

        # Extract the move_ids from the query results
        move_ids = [
            record['move_1_id'],
            record['move_2_id'],
            record['move_3_id'],
            record['move_4_id']
        ]
        # Extract the move pps from the query results
        current_pps = [
            record['move_1_current_pp'],
            record['move_2_current_pp'],
            record['move_3_current_pp'],
            record['move_4_current_pp']
        ]

        # Setup variable to store query results
        moves = []
        # Look at all four moves of the pokemon
        for i in range(4):
            # Ignore if the user has less than 4 moves
            if move_ids[i] is None:
                continue

            # Get the move name and max pp from the moves table (static)
            cursor.execute("SELECT move_name, pp FROM moves WHERE move_id = %s", (move_ids[i],))
            move_row = cursor.fetchone()

            # Error handling
            if not move_row:
                move_name = "Unknown Move"
                max_pp = 0
            else:
                move_name = move_row['move_name']
                max_pp = move_row['pp']

            # Save information about the move in a list
            moves.append({
                "move_name": move_name,
                "current_pp": current_pps[i],
                "max_pp": max_pp
            })

        # DEBUGGING
        # print(f"Fetching moves for user_team_member_id={member_id}")
        # print("Move IDs:", move_ids)
        # for move_id in move_ids:
            # if move_id is not None:
                # cursor.execute("SELECT move_name, pp FROM moves WHERE move_id = %s", (move_id,))
                # move_info = cursor.fetchone()
                # print(f"Move info for ID {move_id}: {move_info}")

        # Send information about the pokemon's moves to performSwitch(newPokemon)
        return jsonify(moves)

    except Exception as e:
        print(f"[EXCEPTION in get_moves] member_id={member_id}, error={e}")
        traceback.print_exc()
        return jsonify({"error": "Move fetch failed"}), 500
    finally:
        if conn:
            conn.close()
