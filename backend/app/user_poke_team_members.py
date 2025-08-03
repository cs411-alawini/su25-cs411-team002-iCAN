from mysql.connector import connect
from mysql.connector.cursor import MySQLCursorDict
from flask import jsonify, render_template, Blueprint
from app.db import getconn


# Routes will go here e.g. @bp.route('/user-poke-team-members')
bp = Blueprint('user_poke_team_members', __name__, url_prefix='/user-poke-team-members', template_folder='templates')

# Route for displaying ALL users' Pokemon team members
# Create the endpoint at url_prefix='/user-poke-team-members'
@bp.route('/', methods=['GET'])
def get_all_user_poke_team_members():
    conn = None
    try:  
        # Get the database connection
        conn = getconn()
        print('Connection open.')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        query = "SELECT * FROM user_poke_team_members ORDER BY user_team_id, user_team_member_id;"
        # Select query
        print('Fetching data...')
        cursor.execute(query)
        print('Data successfully fetched.')
    
        # Fetch the results
        results = cursor.fetchall()
    
        # Print results (for debugging)
        for i in results:
            print(i)
    
        # Close the cursor and return the data as JSON
        cursor.close()
        #return jsonify(results)

        # Rendering results in viewer
        return render_template('user-poke-team-members.html', entries=results)

    except Exception as e:
        print(f"There was an error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            print('Connection closed.')

# Route for displaying ONE team with its members by its user_team_id
# Create the endpoint at url_prefix='/pokedex/1' t
@bp.route('/<int:user_team_id>', methods=['GET'])
def get_one_team_member(user_team_id):
    conn = None
    try:  
        # Get the database connection
        conn = getconn()
        print('Connection open.')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        query = "SELECT * FROM user_poke_team_members WHERE user_team_id= %s;"
        # Select query
        print('Fetching data...')
        cursor.execute(query, (user_team_id))
        print('Data successfully fetched.')
    
        # Fetch the results
        result = cursor.fetchall()
    
        # Print results (for debugging)
        print(result)
    
        # Close the cursor and return the data as JSON
        cursor.close()
        #return jsonify(results)

        # Rendering results in viewer
        return render_template('user-poke-team-members.html', members=result)

    except Exception as e:
        print(f"There was an error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            print('Connection closed.')
    
from flask import request

# Search for user poke team members by user_team_id
@bp.route('/search', methods=['POST'])
def search_user_team_members():
    conn = None
    try:
        user_team_id = request.form.get('user_team_id')
        if not user_team_id:
            return jsonify({"error": "Team ID is required"}), 400

        conn = getconn()
        print('Connection open.')

        cursor = conn.cursor(cursor_class=MySQLCursorDict)

        query = "SELECT * FROM user_poke_team_members WHERE user_team_id = %s;"
        cursor.execute(query, (user_team_id,))
        results = cursor.fetchall()

        cursor.close()
        return render_template('user-poke-team-members.html', members=results)

    except Exception as e:
        print(f"There was an error performing search: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()
            print('Connection closed.')

# Add user poke team members to a recently created user team
# Part 1: Get available moves 
@bp.route('/moves/<int:pokedex_id>', methods=['GET'])
def get_available_moves(pokedex_id):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor(cursor_class=MySQLCursorDict)

        # Get name + image
        cursor.execute("SELECT name, image_url FROM pokedex_entries WHERE pokedex_id = %s;", (pokedex_id,))
        poke_data = cursor.fetchone()
        if not poke_data:
            return jsonify({"error": "Invalid Pokédex ID"}), 404

        # Get moves
        cursor.execute("""
            SELECT m.move_id, m.move_name, m.pp
            FROM pokemon_moves pm
            JOIN moves m ON pm.move_id = m.move_id
            WHERE pm.pokedex_id = %s;
        """, (pokedex_id,))
        moves = cursor.fetchall()

        return jsonify({
            "pokemon": poke_data,
            "moves": moves
        })

    except Exception as e:
        print(f"Error fetching moves: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn: conn.close()

# Part 2 add a new user poke team member
@bp.route('/add', methods=['POST'])
def add_user_team_member():
    conn = None
    try:
        form = request.form
        team_id = int(form['user_team_id'])
        pokedex_id = int(form['pokedex_id'])
        move_ids = [int(form[f'move_{i}_id']) for i in range(1, 5)]

        # Check that all 4 move_ids are unique
        if len(set(move_ids)) != 4:
            return jsonify({"error": "All 4 moves must be different"}), 400

        conn = getconn()
        cursor = conn.cursor(cursor_class=MySQLCursorDict)

        # Count current members on the team
        cursor.execute("SELECT COUNT(*) AS count FROM user_poke_team_members WHERE user_team_id = %s", (team_id,))
        count = cursor.fetchone()['count']
        if count >= 6:
            return jsonify({"error": "Team already has 6 Pokémon"}), 400

        new_member_id = count + 1

        # Get base HP from pokedex_entries
        cursor.execute("SELECT hp FROM pokedex_entries WHERE pokedex_id = %s", (pokedex_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": f"Pokedex ID {pokedex_id} not found"}), 400
        current_hp = row['hp']

        # Get PP values for each move
        pp_values = []
        for move_id in move_ids:
            cursor.execute("SELECT pp FROM moves WHERE move_id = %s", (move_id,))
            move_row = cursor.fetchone()
            if not move_row:
                return jsonify({"error": f"Move ID {move_id} not found"}), 400
            pp_values.append(int(move_row['pp']))

        # Insert new team member with current_hp
        insert_query = """
            INSERT INTO user_poke_team_members (
                user_team_id, user_team_member_id, pokedex_id, current_hp,
                move_1_id, move_1_current_pp,
                move_2_id, move_2_current_pp,
                move_3_id, move_3_current_pp,
                move_4_id, move_4_current_pp
            )
            VALUES (%s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s)
        """
        cursor.execute(insert_query, (
            team_id, new_member_id, pokedex_id, current_hp,
            move_ids[0], pp_values[0],
            move_ids[1], pp_values[1],
            move_ids[2], pp_values[2],
            move_ids[3], pp_values[3]
        ))
        conn.commit()
        cursor.close()
        return redirect(url_for('user_poke_team_members.get_all_user_poke_team_members'))

    except Exception as e:
        print(f"There was an error adding a team member: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()

# Delete a user poke team member
@bp.route('/delete', methods=['POST'])
def delete_team_member():
    conn = None
    try:
        team_id = request.form.get('user_team_id')
        member_id = request.form.get('user_team_member_id')

        conn = getconn()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM user_poke_team_members
            WHERE user_team_id = %s AND user_team_member_id = %s
        """, (team_id, member_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('user_poke_team_members.get_all_user_poke_team_members'))

    except Exception as e:
        print(f"Error deleting member: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn: conn.close()

# Update a user poke team member's moves
# Part 1: Make edits to moves
@bp.route('/edit', methods=['GET'])
def edit_team_member():
    conn = None
    try:
        team_id = request.args.get('user_team_id')
        member_id = request.args.get('user_team_member_id')

        conn = getconn()
        cursor = conn.cursor(cursor_class=MySQLCursorDict)

        # Get team member
        cursor.execute("""
            SELECT * FROM user_poke_team_members
            WHERE user_team_id = %s AND user_team_member_id = %s
        """, (team_id, member_id))
        member = cursor.fetchone()
        if not member:
            return jsonify({"error": "Team member not found"}), 404

        # Get Pokémon info
        cursor.execute("SELECT name, image_url FROM pokedex_entries WHERE pokedex_id = %s", (member['pokedex_id'],))
        pokemon = cursor.fetchone()

        # Get legal moves
        cursor.execute("""
            SELECT m.move_id, m.move_name, m.pp
            FROM pokemon_moves pm
            JOIN moves m ON pm.move_id = m.move_id
            WHERE pm.pokedex_id = %s
        """, (member['pokedex_id'],))
        legal_moves = cursor.fetchall()

        cursor.close()

        return render_template("edit-team-member.html", member=member, pokemon=pokemon, legal_moves=legal_moves)

    except Exception as e:
        print(f"Error rendering edit form: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn: conn.close()

# Implement update
@bp.route('/update', methods=['POST'])
def update_team_member():
    conn = None
    try:
        form = request.form
        team_id = int(form['user_team_id'])
        member_id = int(form['user_team_member_id'])
        move_ids = [int(form[f'move_{i}_id']) for i in range(1, 5)]

        if len(set(move_ids)) != 4:
            return jsonify({"error": "All 4 moves must be different"}), 400

        conn = getconn()
        cursor = conn.cursor(cursor_class=MySQLCursorDict)

        # Get PP for each move
        pp_values = []
        for move_id in move_ids:
            cursor.execute("SELECT pp FROM moves WHERE move_id = %s", (move_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": f"Move ID {move_id} not found"}), 400
            pp_values.append(int(row['pp']))

        # Update team member
        update_query = """
            UPDATE user_poke_team_members
            SET
                move_1_id = %s, move_1_current_pp = %s,
                move_2_id = %s, move_2_current_pp = %s,
                move_3_id = %s, move_3_current_pp = %s,
                move_4_id = %s, move_4_current_pp = %s
            WHERE user_team_id = %s AND user_team_member_id = %s
        """
        cursor.execute(update_query, (
            move_ids[0], pp_values[0],
            move_ids[1], pp_values[1],
            move_ids[2], pp_values[2],
            move_ids[3], pp_values[3],
            team_id, member_id
        ))
        conn.commit()
        cursor.close()

        return redirect(url_for('user_poke_team_members.get_all_user_poke_team_members'))

    except Exception as e:
        print(f"Error updating team member: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn: conn.close()



