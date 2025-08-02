from flask import jsonify, render_template, Blueprint, request, session
from app.db import getconn


# Routes will go here e.g. @bp.route('/login')
bp = Blueprint('login', __name__, url_prefix='/login', template_folder='templates')

# Create the endpoint at url_prefix='/login'
@bp.route('/', methods=['POST','GET'])
def login():
    """
    The user has submitted a form, by pressing a submit/login/signup button on
        login.html. 
    We will sign the user up for the game, or log them in.
    """

    # User has submitted a form on login.html
    if request.method == 'POST':
        # Setup and get information
        form_type = request.form.get('form_type')
        username = request.form.get('user_id')
        password = request.form.get('pwd')
        email = request.form.get('email')
    
        # Setup to connect to GCP and to write SQL
        db_conn = getconn()
        sql_cursor = db_conn.cursor()

        # User initiated SIGN UP
        if form_type == 'signup':
            # Check if user already exists
            check_user_query = "SELECT * FROM Users WHERE user_name = %s"
            sql_cursor.execute(check_user_query, (username,))
            existing_username = sql_cursor.fetchone()

            if existing_username:
                return "Username already exists."

            # Insert new user
            new_user_query = "INSERT INTO Users (user_name, pwd) VALUES (%s, %s)"
            sql_cursor.execute(new_user_query, (username, password))
            db_conn.commit()
            return "Signup successful! Please log in."


        # User initiated LOGIN
        elif form_type == 'login':

            # Check if username already exists
            check_user_query = "SELECT * FROM Users WHERE user_name = %s AND pwd = %s"
            sql_cursor.execute(check_user_query, (username, password))
            existing_user = sql_cursor.fetchone()

            if existing_user:
                session['username'] = username
                return redirect(url_for('main.homepage'))
            else:
                return "Incorrect username or password."
        
        else:
            return "Unknown form type was submitted."


    return render_template('login.html')

 