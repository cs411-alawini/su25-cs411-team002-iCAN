from flask import jsonify, render_template, Blueprint, request, session, redirect, url_for
from app.db import getconn


# Routes will go here e.g. @bp.route('/auth')
bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

# Create the endpoint at url_prefix='/auth'
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

        print(form_type, username, password, email)
    
        # Setup to connect to GCP
        db_conn = getconn()
 

        try:
            # Open "context manager" for sql_cursor (auto-ends)
            with db_conn.cursor() as sql_cursor:
            
                # Set isolation level - we do not want write-write conflicts
                # There should only be unique usernames
                sql_cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")

                # User initiated SIGN UP
                if form_type == 'signup':
                    # Check if user already exists
                    check_user_query = "SELECT * FROM users WHERE user_name = %s"
                    sql_cursor.execute(check_user_query, (username,))
                    existing_username = sql_cursor.fetchone()

                    if existing_username:
                        return "Username already exists."

                    # Insert new user using the STORED PROCEDURE AddNewUser
                    new_user_query = "INSERT INTO users (user_name, pwd, email, is_active) VALUES (%s, %s, %s, %s)"
                    sql_cursor.execute(new_user_query, (username, password, email, 1))
                    db_conn.commit()

                    session['username'] = username
                    user_id = existing_user[0]
                    session['user_id'] = user_id
                    
                    print("Signup successful! Please log in.") 
                    return redirect(url_for('home.load_homepage'))


                # User initiated LOGIN
                elif form_type == 'login':
                    # Check if username already exists
                    check_user_query = "SELECT * FROM users WHERE user_name LIKE %s AND pwd = %s"
                    sql_cursor.execute(check_user_query, (f"%{username}%", password))
                    existing_user = sql_cursor.fetchone()
                    print(f"existing_user results = {existing_user}")


                    # Get user_id
                    get_user_id = "SELECT user_id FROM users WHERE user_name LIKE %s AND pwd = %s"
                    sql_cursor.execute(get_user_id, (f"%{username}%", password))
                    user_id = sql_cursor.fetchone()

                    if existing_user:
                        session['username'] = username
                        session['user_id'] = user_id['user_id']
                        return redirect(url_for('home.load_homepage'))
                    else:
                        return "Incorrect username or password."
                
                else:
                    return "Unknown form type was submitted."

            # Close connection to GCP
        finally:
            db_conn.close()
    return render_template('login.html')

 