# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from db_config import get_db_connection, get_dict_cursor
import psycopg2

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change this or load from .env

# List of all tables and columns referencing users
REFERENCING_COLUMNS = [
    ("visitor", "hostuser_id"),
    ("budget", "user_id"),
    ("expense", "user_id"),
    ("expense", "approvedby_userid"),
    ("schedule", "createdby"),
    ("task", "createdby"),
    ("remainder", "createdby"),
    ("user_contact", "user_id"),
    ("user_attendance", "user_id"),
    ("assign_to", "user_id")
]


# ---------------- HOME (SHOW ALL USERS) ---------------- #
@app.route('/')
def index():
    conn = get_db_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT 
            u.user_id,
            u.role,
            u.firstname,
            u.lastname,
            u.email,
            u.salary,
            s.firstname AS supervisor_first,
            s.lastname AS supervisor_last
        FROM users u
        LEFT JOIN users s ON u.supervisor_id = s.user_id
        ORDER BY u.user_id;
    """)
    users = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('index.html', users=users)


# ---------------- ADD USER ---------------- #
@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user_id = request.form.get('user_id') or None
        role = request.form['role']
        firstname = request.form['firstname']
        lastname = request.form.get('lastname')
        email = request.form['email']
        salary = request.form.get('salary') or None
        supervisor_id = request.form.get('supervisor_id') or None

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            if user_id:
                cur.execute("""
                    INSERT INTO users (user_id, role, firstname, lastname, email, salary, supervisor_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                """, (user_id, role, firstname, lastname, email, salary, supervisor_id))
            else:
                cur.execute("""
                    INSERT INTO users (role, firstname, lastname, email, salary, supervisor_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                """, (role, firstname, lastname, email, salary, supervisor_id))

            new_id = cur.fetchone()[0]
            conn.commit()
            flash(f"✅ User added successfully (ID: {new_id})", "success")

        except psycopg2.IntegrityError as e:
            conn.rollback()
            flash(f"❌ Error adding user: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('index'))

    # GET request: fetch supervisors for dropdown
    conn = get_db_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT user_id, firstname, lastname FROM users ORDER BY firstname;")
    supervisors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_user.html', supervisors=supervisors)


# ---------------- UPDATE USER ---------------- #
@app.route('/user/update/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    conn = get_db_connection()
    cur = get_dict_cursor(conn)

    if request.method == 'POST':
        role = request.form['role']
        firstname = request.form['firstname']
        lastname = request.form.get('lastname')
        email = request.form['email']
        salary = request.form.get('salary') or None
        supervisor_id = request.form.get('supervisor_id') or None

        try:
            cur2 = conn.cursor()
            cur2.execute("""
                UPDATE users
                SET role=%s, firstname=%s, lastname=%s, email=%s, salary=%s, supervisor_id=%s
                WHERE user_id=%s;
            """, (role, firstname, lastname, email, salary, supervisor_id, user_id))
            conn.commit()
            flash("ℹ️ User updated successfully!", "info")

        except psycopg2.IntegrityError as e:
            conn.rollback()
            flash(f"❌ Error updating user: {str(e)}", "danger")

        finally:
            cur2.close()
            cur.close()
            conn.close()

        return redirect(url_for('index'))

    # GET request — show user data
    cur.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
    user = cur.fetchone()
    cur.execute("SELECT user_id, firstname, lastname FROM users WHERE user_id <> %s ORDER BY firstname;", (user_id,))
    supervisors = cur.fetchall()

    cur.close()
    conn.close()

    if not user:
        flash("❌ User not found.", "danger")
        return redirect(url_for('index'))

    return render_template('update_user.html', user=user, supervisors=supervisors)


# ---------------- DELETE USER ---------------- #
@app.route('/user/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Nullify references in all dependent tables
        for table, col in REFERENCING_COLUMNS:
            sql = f"UPDATE {table} SET {col} = NULL WHERE {col} = %s;"
            cur.execute(sql, (user_id,))

        # Also nullify supervisor links
        cur.execute("UPDATE users SET supervisor_id = NULL WHERE supervisor_id = %s;", (user_id,))

        # Delete the user itself
        cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id;", (user_id,))
        deleted = cur.fetchone()

        if deleted:
            conn.commit()
            flash(f"🗑️ User ID {user_id} deleted successfully.", "danger")
        else:
            conn.rollback()
            flash("⚠️ User not found or already deleted.", "warning")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error deleting user: {str(e)}", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index'))


# ---------------- RUN APP ---------------- #
if __name__ == '__main__':
    app.run(debug=True)
