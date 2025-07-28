from flask import jsonify, render_template, Blueprint
from app.db import getconn


# Routes will go here e.g. @bp.route('/pokedex')
bp = Blueprint('pokedex', __name__, url_prefix='/pokedex', template_folder='templates')

# Create the endpoint at url_prefix='/pokedex'
@bp.route('/', methods=['GET'])
def get_all_pokemon():
    conn = None
    try:  
        # Get the database connection
        conn = getconn()
        print('Connection open.')
    
        # Create a cursor to execute queries and return in a dict format
        cursor = conn.cursor()
    
        # Select query
        print('Fetching data...')
        cursor.execute("SELECT * FROM pokedex_entries ORDER BY pokedex_id;")
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
        return render_template('pokedex.html', entries=results)
    

    except Exception as e:
        print(f"There was an error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
  
    finally: 
        # Close the connection
        if conn is not None:
            conn.close()
            print('Connection closed.')


# Create the endpoint at url_prefix='/pokedex/1'
# @bp.route('/<int:pokedex_id>', methods=(['GET']))
# def get_one_pokemon(pokedex_id):
    