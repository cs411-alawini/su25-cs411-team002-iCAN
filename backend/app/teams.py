from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn


# Routes will go here e.g. @bp.route('/auth')
bp = Blueprint('teams', __name__, url_prefix='/teams', template_folder='templates')

# Create the endpoint at url_prefix='/teams'
@bp.route('/create', methods=['POST', 'GET'])
def create_team():
    """
    Create a new team for the user.
    """
    
    if request.method == 'POST':
        # What the user typed in 
        pokemon_name = request.form.get('pokemon_name')


    return render_template('create_team.html')

