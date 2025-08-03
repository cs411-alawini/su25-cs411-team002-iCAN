from flask import jsonify, render_template, Blueprint
from app.db import getconn


# Routes will go here e.g. @bp.route('/user-teams')
bp = Blueprint('user_teams', __name__, url_prefix='/user-teams', template_folder='templates')

# Route for displaying ALL user teams
# Create the endpoint at url_prefix='/user-teams'
@bp.route('/', methods=['GET'])
def get_all_user_teams():
    conn = None
    try:  
        # Get the database connection
        conn = getconn()
        print('Connection open.')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        query = "SELECT * FROM user_teams ORDER BY user_team_id;"
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
        return render_template('user-teams.html', entries=results)

    except Exception as e:
        print(f"There was an error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            print('Connection closed.')

# Route for displaying ONE user team by its ID
# Create the endpoint at url_prefix='/user-teams/1' t
@bp.route('/<int:user_team_id>', methods=['GET'])
def get_one_user_team(user_team_id):
    conn = None
    try:  
        # Get the database connection
        conn = getconn()
        print('Connection open.')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        query = "SELECT * FROM user_teams WHERE user_team_id= %s;"
        # Select query
        print('Fetching data...')
        cursor.execute(query, (user_team_id))
        print('Data successfully fetched.')
    
        # Fetch the results
        result = cursor.fetchone()
    
        # Print results (for debugging)
        print(result)
    
        # Close the cursor and return the data as JSON
        cursor.close()
        #return jsonify(results)

        # Rendering results in viewer
        return render_template('user-teams.html', user_team=result)

    except Exception as e:
        print(f"There was an error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            print('Connection closed.')

from flask import request, redirect, url_for
import mysql.connector
from mysql.connector import connect



from flask import request, redirect, url_for, session, jsonify

from app.db import getconn

# Route for creating a new team
@bp.route('/create', methods=['POST'])
def create_user_team():
    conn = None
    try:
        # Get form input
        team_name = request.form.get('team_name')
        if not team_name:
            return jsonify({"error": "Team name is required"}), 400
        if len(team_name) > 30:
            return jsonify({"error": "Team name must be 30 characters or fewer"}), 400

        # Get logged-in user's ID
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not logged in"}), 401

        # Connect to DB
        conn = getconn()
        cursor = conn.cursor()

        # Get next available user_team_id
        cursor.execute("SELECT (MAX(user_team_id)) FROM user_teams;")
        max_id = cursor.fetchone()[0]
        new_team_id = max_id + 1

        # Insert the new team
        insert_query = """
            INSERT INTO user_teams (user_id, user_team_id, is_active, team_name)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (user_id, new_team_id, True, team_name))
        conn.commit()

        cursor.close()
        return redirect(url_for('user_teams.get_all_user_teams'))

    except Exception as e:
        print(f"There was an error creating the team: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()
