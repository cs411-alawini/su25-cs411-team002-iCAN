"""
From Mengmeng
"""
from flask import Flask, render_template, request, redirect, url_for, Blueprint
from datetime import datetime
import sqlite3
import random

# Routes will go here e.g. @bp.route('/battle')
bp = Blueprint('battles', __name__, url_prefix='/battle', template_folder='templates')


def get_db_connection():
    conn = sqlite3.connect('your_database.db')
    conn.row_factory = sqlite3.Row
    return conn



@bp.route('/start', methods=['GET', 'POST'])
def start_battle():
    conn = get_db_connection()

    # Get lists for dropdowns
    user_teams = conn.execute("SELECT * FROM user_poke_team_members JOIN battles USING(user_team_id)").fetchall()
    gyms = conn.execute("SELECT * FROM gym_leader_team_members JOIN battles USING(gym_id)").fetchall()

    # Predefine placeholders
    user_team = []
    gym_team = []
    selected_user_team_id = None
    selected_gym_id = None

    if request.method == 'POST':
        battle_id = request.form['battle_id']
        selected_user_team_id = request.form['user_team_id']
        selected_gym_id = request.form['gym_id']

        # Fetch team previews
        user_team = conn.execute("""
            SELECT * FROM user_poke_team_members 
            JOIN battles USING(user_team_id)
            WHERE user_team_id = ?
        """, (selected_user_team_id,)).fetchall()

        gym_team = conn.execute("""
            SELECT * FROM gym_leader_team_members 
            JOIN battles USING(gym_id)
            WHERE gym_id = ?
        """, (selected_gym_id,)).fetchall()

        # Simulate battle and save result
        start_time = datetime.now()
        win_loss_outcome = random.choice([0, 1])
        end_time = datetime.now()

        conn.execute("""
            INSERT INTO battles (battle_id, user_team_id, gym_id, start_time, end_time, win_loss_outcome)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (battle_id, selected_user_team_id, selected_gym_id, start_time, end_time, win_loss_outcome))
        conn.commit()

        badge = None
        if win_loss_outcome == 1:
            badge = conn.execute("""
                SELECT badge_title, badge_image 
                FROM gym_leaders NATURAL JOIN battles 
                WHERE gym_id = ?
            """, (selected_gym_id,)).fetchone()

        conn.close()

        return render_template("battle_home.html",
                               user_teams=user_teams,
                               gyms=gyms,
                               user_team=user_team,
                               gym_team=gym_team,
                               badge=badge,
                               battle_id=battle_id,
                               outcome=win_loss_outcome,
                               start=start_time,
                               end=end_time,
                               selected_user_team_id=int(selected_user_team_id),
                               selected_gym_id=int(selected_gym_id))

    # GET request
    conn.close()
    return render_template("battle_home.html",
                           user_teams=user_teams,
                           gyms=gyms,
                           user_team=user_team,
                           gym_team=gym_team)