from flask import jsonify, render_template, Blueprint, request
from app.db import getconn

bp = Blueprint('pokedex', __name__, url_prefix='/pokedex', template_folder='templates')

# Route for displaying ALL Pokémon
@bp.route('/', methods=['GET'])
def get_all_pokemon():
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        get_all_pokemon = "SELECT * FROM pokedex_entries ORDER BY pokedex_id;"
        cursor.execute(get_all_pokemon)
        all_pokemon = cursor.fetchall()
        cursor.close()

        return render_template('pokedex.html', entries=all_pokemon)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()

# Route for displaying a Pokémon by NAME
@bp.route('/search/<string:name>', methods=['GET'])
def get_pokemon_by_name(name):
    conn = None
    try:
        conn = getconn()
        cursor = conn.cursor()

        get_pokemon_name = "SELECT * FROM pokedex_entries WHERE LOWER(name) LIKE LOWER(%s);"
        cursor.execute(get_pokemon_name, (f"%{name}%",))
        pokemon_name = cursor.fetchone()
        cursor.close()

        return render_template('pokedex.html', pokemon=pokemon_name)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn is not None:
            conn.close()