from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn

# Routes will go here e.g. @bp.route('/')
bp = Blueprint('home', __name__, url_prefix='/', template_folder='templates')


# Manage what HTML/route we're on
@bp.route('/')
def root():
    """
    An intermediate page to determine whether a user needs to re-login, or if they
        can load straight to the home page. This is necessary for dealing with 
        expired sessions.
    """
    # Deal with asking user to re-login
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('home.load_homepage'))

# Create the endpoint at url_prefix='/home'
@bp.route('/home', methods=['POST','GET'])
def load_homepage():
    """
    The user has logged in or signed up for the game and is now brought
        to the Pokemon Boss Rush Homepage.
    """
    username = session.get('username')
    return render_template('homepage.html', user=username)

# Create the endpoint at url_prefix='/profile'
@bp.route('/profile', methods=['POST','GET'])
def load_profile():
    """
    The user has clicked the Profile button from the homepage
    """
    username = session.get('username')
    return render_template('profile.html', user=username, badge_level="badge level")

# Create the endpoint at url_prefix='/teams'
@bp.route('/teams', methods=['POST','GET'])
def load_teams():
    """
    The user has clicked the Teams button from the homepage
    """

    return render_template('all_teams.html')

# Create the endpoint at url_prefix='/battle'
@bp.route('/battle', methods=['POST','GET'])
def load_battle():
    """
    The user has clicked the Enter Gym button from the homepage
    """

    return render_template('battle.html')

