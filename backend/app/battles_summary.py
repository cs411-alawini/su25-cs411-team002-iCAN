from flask import Blueprint, render_template, request
from app.db import conn  

bp = Blueprint('battles', __name__, url_prefix='/battles', template_folder='templates')

@bp.route('/summary', methods=['GET', 'POST'])
def get_battle_summary():
    if request.method == 'POST':
        battle_id = request.form.get('battle_id')
        user_team_id = request.form.get('user_team_id')
        gym_id = request.form.get('gym_id')
    else:
        battle_id = request.args.get('battle_id')
        user_team_id = request.args.get('user_team_id')
        gym_id = request.args.get('gym_id')

    if not battle_id or not user_team_id or not gym_id:
        return "Missing battle_id, user_team_id or gym_id", 400

    try:
        with conn.cursor() as cur:
            # Get battle row
            cur.execute("""
                SELECT * FROM battles
                WHERE battle_id = %s AND user_team_id = %s AND gym_id = %s
            """, (battle_id, user_team_id, gym_id))
            battle = cur.fetchone()

            if not battle:
                return "Battle not found", 404

            # Get user team
            cur.execute("""
                SELECT * FROM user_poke_team_members
                WHERE user_team_id = %s
            """, (user_team_id,))
            user_team = cur.fetchall()

            # Get gym team
            cur.execute("""
                SELECT * FROM gym_leader_team_members
                WHERE gym_id = %s
            """, (gym_id,))
            gym_team = cur.fetchall()

            # Get badge if win
            badge = None
            if battle['win_loss_outcome'] == 1:
                cur.execute("""
                    SELECT badge_title, badge_image
                    FROM gym_leaders
                    WHERE gym_id = %s
                """, (gym_id,))
                badge = cur.fetchone()

    except Exception as e:
        return f"Database error: {e}", 500

    return render_template("battles_summary.html",
                           battle_id=battle['battle_id'],
                           start=battle['start_time'],
                           end=battle['end_time'],
                           outcome=battle['win_loss_outcome'],
                           user_team=user_team,
                           gym_team=gym_team,
                           badge=badge)