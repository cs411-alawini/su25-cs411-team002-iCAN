from flask import jsonify, render_template, Blueprint
from app.db import getconn

# Routes will go here e.g. @bp.route('/gyms')
bp = Blueprint('gym', __name__, url_prefix='/gym')

# Route for selecting a gym leader
# Create the endpoint at url_prefix='/gyms'
@bp.route('/', methods=['GET'])
def select_gym_leader():
    """
    The user has selected the Gyms button from the homepage, or the Enter Gym button on the homepage,
        or the enter gym battle on the profile page. Load all the gyms on gym.html.
    """
    conn = None
    try:  
        # Get the database connection
        conn = getconn()

        # DEBUGGING
        # print('Connection open for select_gym_leader()')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        # Get all the gym_leader information
        query = "SELECT * FROM gym_leaders ORDER BY gym_id;"
        # print('Fetching data...')
        cursor.execute(query)
        # print('Data successfully fetched.')
    
        # Fetch the results - all the gym_leader information
        results = cursor.fetchall()
    
        # DEBUGGING - print query results
        # for i in results:
            # print(i)
    
        # Close the cursor and return the data as JSON
        cursor.close()

        # Send gym leader information from query to Jinja
        return render_template('gym.html', leaders=results)

    except Exception as e:
        print(f"There was an error fetching data in select_gym_leader(): {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            # print('Connection closed in select_gym_leader()')