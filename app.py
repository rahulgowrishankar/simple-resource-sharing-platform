"""
College Resource Sharing App
-----------------------------
Students can upload PDFs, browse approved resources, and ask the AI chatbot
questions about uploaded content. Moderators review submissions before they
go live.
 
Setup:
  1. Run schema.sql to create the database and tables.
  2. Set your MySQL credentials in a .env file (see DB_CONFIG below).
  3. To promote a user to moderator, run this in MySQL:
        UPDATE users SET role = 'moderator' WHERE email = 'someone@college.edu';
"""
from flask import jsonify
from dotenv import load_dotenv

load_dotenv() #reads .env file

from ai.pdf_processor import extract_text_from_pdf, split_into_chunks
from ai.vector_store import store_chunks, search_similar_chunks
from ai.chatbot import generate_answer







from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "a-safe-local-development-string")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---- Fill in your MySQL details here ----
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",   # <-- your MySQL password
    "database": "simple_resources",
    "ssl_disabled": True
}


def get_db():
    """Open a connection to MySQL. Called inside every route that needs data."""
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# HOME PAGE — shows only APPROVED resources
# ============================================================

@app.route("/")
def home():
    search_query = request.args.get("q", "").strip()
    selected_semester = request.args.get("semester", "").strip()
    selected_subject = request.args.get("subject", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    sql_query = """
        SELECT r.*, ROUND(AVG(rt.rating_value), 1) AS avg_rating
        FROM resources r
        LEFT JOIN ratings rt ON r.id = rt.resource_id
        WHERE r.status = 'approved'
    """
    query_params = []

    if search_query:
        sql_query += " AND r.title LIKE %s"
        query_params.append(f"%{search_query}%")

    if selected_semester:
        sql_query += " AND r.semester = %s"
        query_params.append(selected_semester)

    if selected_subject:
        sql_query += " AND r.subject = %s"
        query_params.append(selected_subject)

    sql_query += " GROUP BY r.id ORDER BY r.id DESC"

    cursor.execute(sql_query, tuple(query_params))
    resources = cursor.fetchall()

    cursor.execute("SELECT DISTINCT subject FROM resources WHERE status = 'approved' ORDER BY subject ASC")
    available_subjects = [row["subject"] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        "home.html",
        resources=resources,
        search_query=search_query,
        selected_semester=selected_semester,
        selected_subject=selected_subject,
        available_subjects=available_subjects
    )


# ============================================================
# RATING SUBMISSION
# ============================================================

@app.route("/rate/<int:resource_id>", methods=["POST"])
def rate_resource(resource_id):
    rating_value = request.form.get("rating")
    if rating_value and rating_value.isdigit():
        val = int(rating_value)
        if 1 <= val <= 5:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ratings (resource_id, rating_value) VALUES (%s, %s)",
                (resource_id, val)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("Rating submitted!")
    return redirect(url_for("home"))


# ============================================================
# REGISTER — hash the password before storing
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Hashed password
        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            conn.commit()
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("That email is already registered.")
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


# ============================================================
# LOGIN — check password with werkzeug, store role in session
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        # check_password_hash compares the plain input against the stored hash
        if user and check_password_hash(user["password"], password):
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]   # 'student' or 'moderator'
            flash(f"Welcome, {user['name']}!")
            return redirect(url_for("home"))
        else:
            flash("Wrong email or password.")

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("home"))


# ============================================================
# UPLOAD — goes to 'pending'; moderator must approve it
# ============================================================

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_name" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"]
        semester = request.form["semester"]
        file = request.files["file"]

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO resources (title, subject, semester, filename, uploaded_by, status) VALUES (%s, %s, %s, %s, %s, 'pending')",
            (title, subject, semester, file.filename, session["user_name"])
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Resource uploaded! It will appear on the dashboard once a moderator approves it.")
        return redirect(url_for("my_uploads"))

    return render_template("upload.html")


# ============================================================
# MY UPLOADS — shows the logged-in user's resources + their status
# ============================================================

@app.route("/my-uploads")
def my_uploads():
    if "user_name" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM resources WHERE uploaded_by = %s ORDER BY id DESC",
        (session["user_name"],)
    )
    resources = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_uploads.html", resources=resources)


# ============================================================
# DELETE — uploader can delete their own resource
# ============================================================

@app.route("/delete/<int:resource_id>")
def delete_resource(resource_id):
    if "user_name" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT uploaded_by, filename FROM resources WHERE id = %s", (resource_id,))
    resource = cursor.fetchone()

    if not resource:
        flash("Resource not found.")
        cursor.close()
        conn.close()
        return redirect(url_for("home"))

    # Only the uploader (or a moderator) can delete
    if resource["uploaded_by"] != session["user_name"] and session.get("user_role") != "moderator":
        flash("Access Denied! You can only delete your own resources.")
        cursor.close()
        conn.close()
        return redirect(url_for("home"))

    filepath = os.path.join(UPLOAD_FOLDER, resource["filename"])
    if os.path.exists(filepath):
        os.remove(filepath)

    cursor.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Resource deleted.")
    return redirect(url_for("home"))

# ============================================================
# MODERATOR PANEL — list pending resources, approve or reject
# ============================================================

@app.route("/moderator")
def moderator():
    # Only moderators can access this page
    if session.get("user_role") != "moderator":
        flash("Access denied. Moderators only.")
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resources WHERE status = 'pending' ORDER BY id DESC")
    pending = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("moderator.html", pending=pending)


@app.route("/approve/<int:resource_id>")
def approve_resource(resource_id):
    if session.get("user_role") != "moderator":
        flash("Access denied.")
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch resource details to find the file path on disk
    cursor.execute("SELECT filename, title FROM resources WHERE id = %s", (resource_id,))
    resource = cursor.fetchone()
    
    if not resource:
        cursor.close()
        conn.close()
        flash("Resource not found.")
        return redirect(url_for("moderator"))

    # 2. Extract and Process the PDF into the AI Vector Store
    ai_status = ""
    filepath = os.path.join(UPLOAD_FOLDER, resource["filename"])
    
    if os.path.exists(filepath):
        try:
            # Parse document contents using your correct imported functions
            raw_text = extract_text_from_pdf(filepath)
            
            # FIXED HERE: Using split_into_chunks to match your top import statement!
            text_chunks = split_into_chunks(raw_text)
            
            # Save vectors to ChromaDB linked to this specific resource ID
            store_chunks(resource_id, text_chunks)
            ai_status = " and indexed for AI chat"
        except Exception as e:
            # Failsafe: logs problem but doesn't crash approval flow
            ai_status = f" (Warning: AI indexing failed: {str(e)})"
    else:
        ai_status = " (Warning: Physical PDF file missing, skipped AI indexing)"

    # 3. Approve in Database
    cursor.execute("UPDATE resources SET status = 'approved' WHERE id = %s", (resource_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Resource '{resource['title']}' approved{ai_status}!")
    return redirect(url_for("moderator"))

@app.route("/reject/<int:resource_id>")
def reject_resource(resource_id):
    if session.get("user_role") != "moderator":
        flash("Access denied.")
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch filename from DB to cleanly sweep it off your local disk storage
    cursor.execute("SELECT filename FROM resources WHERE id = %s", (resource_id,))
    resource = cursor.fetchone()

    if resource:
        # Delete the physical file from the local disk system folder pathway
        filepath = os.path.join(UPLOAD_FOLDER, resource["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
            
        # 2. Wipe the file entry completely out of your MySQL data tables
        cursor.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
        conn.commit()

    cursor.close()
    conn.close()

    flash("Resource rejected and removed completely.")
    return redirect(url_for("moderator"))

# ============================================================
# DOWNLOAD
# ============================================================

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)




@app.route("/process-pdf/<int:resource_id>")
def process_pdf(resource_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT filename FROM resources WHERE id = %s", (resource_id,))
    resource = cursor.fetchone()

    if not resource:
        cursor.close()
        conn.close()
        flash("Resource entry not found.")
        return redirect(url_for("home"))

    file_path = os.path.join(UPLOAD_FOLDER, resource['filename'])

    try:
        raw_text = extract_text_from_pdf(file_path)
        chunks = split_into_chunks(raw_text)
        store_chunks(resource_id, chunks)

        cursor.execute("""
            INSERT INTO pdf_text (resource_id, processed_status) 
            VALUES (%s, 'Processed')
            ON DUPLICATE KEY UPDATE processed_status = 'Processed'
        """, (resource_id,))
        conn.commit()
        flash("PDF processed and added to AI knowledge base!")
    except Exception as e:
        flash(f"AI Processing failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("home"))

@app.route("/ask", methods=["POST"])
def ask_ai():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    
    if not question:
        return jsonify({"error": "Question parameter missing"}), 400
        
    try:
        matched_chunks = search_similar_chunks(question, n_results=5)
        if not matched_chunks:
            return jsonify({"answer": "No resources have been indexed by the AI yet. Please process a PDF resource first."})
            
        ai_response = generate_answer(question, matched_chunks)
        return jsonify({"answer": ai_response})
    except Exception as e:
        # This will force the REAL error message to print in your black command prompt!
        print("\n" + "="*50)
        print("AI CRASH DETECTED:")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        return jsonify({"error": str(e)}), 500

@app.route("/chat")
def chat():
    return render_template("chat.html")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, port=5002)
