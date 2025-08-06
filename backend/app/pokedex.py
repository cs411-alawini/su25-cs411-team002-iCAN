from flask import jsonify, render_template, Blueprint, request
from app.db import getconn

bp = Blueprint('pokedex', __name__, url_prefix='/pokedex', template_folder='templates')

# Route for displaying ALL Pokemon
@bp.route('/', methods=['GET'])
def get_all_pokemon():
    """
    The user has pressed the Pokedex button from the hompage. Display all the pokemon
        from the pokedex, grabbing information from the database.
    """
    conn = None
    try:
        # Open GCP and cursor for queries
        conn = getconn()
        cursor = conn.cursor()

        # Get ALL information about ALL pokemon in the pokedex in our DB
        get_all_pokemon = "SELECT * FROM pokedex_entries ORDER BY pokedex_id;"
        cursor.execute(get_all_pokemon)
        all_pokemon = cursor.fetchall()
        cursor.close()

        # Send dictionary of information to Jinja. It will handle
        # formatting and displaying all that information
        return render_template('pokedex.html', entries=all_pokemon)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()

# Route for displaying a Pokemon by NAME
@bp.route('/search/<string:name>', methods=['GET'])
def get_pokemon_by_name(name):
    """
    The user has initiated a search by pokemon name on the pokedex page.
        Use the submitted name, by the user, and try to find the corresponding
        pokemon. 
    """
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        # Match the user's name search with a name from the database
        get_pokemon_name = "SELECT * FROM pokedex_entries WHERE LOWER(name) LIKE LOWER(%s);"
        cursor.execute(get_pokemon_name, (f"%{name}%",))
        pokemon_name = cursor.fetchone()
        cursor.close()

        # Send the pokemon's name from the database to Jinja to display results
        return render_template('pokedex.html', pokemon=pokemon_name)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()