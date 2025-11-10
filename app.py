from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# -----------------------------
# DB config - change if needed
# -----------------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sql123',
    'database': 'capstoneprojectdb'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print("DB connect error:", e)
        return None

# -----------------------------
# Home / Index
# -----------------------------
@app.route('/')
def home():
    return render_template('index.html')

# -----------------------------
# Login
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # populate dropdowns
    cursor.execute("SELECT Name, Faculty_ID FROM Faculty")
    faculty_list = cursor.fetchall()
    cursor.execute("SELECT Name, SRN FROM Student")
    student_list = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.method == 'POST':
        role = request.form.get('role')
        if role == 'faculty':
            faculty_id = request.form.get('faculty_id')
            session['role'] = 'faculty'
            session['faculty_id'] = faculty_id
            flash("Logged in as Faculty", "success")
            return redirect(url_for('faculty_dashboard'))
        elif role == 'student':
            srn = request.form.get('srn')
            session['role'] = 'student'
            session['srn'] = srn
            flash("Logged in as Student", "success")
            return redirect(url_for('student_dashboard'))
        elif role == 'admin':
            session['role'] = 'admin'
            flash("Logged in as Admin", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Select a valid role", "danger")

    return render_template('login.html', faculty_list=faculty_list, student_list=student_list)

# -----------------------------
# Logout (explicit endpoint so url_for('logout') works)
# -----------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# -----------------------------
# Faculty routes
# -----------------------------
@app.route('/faculty/dashboard')
def faculty_dashboard():
    if session.get('role') != 'faculty':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    faculty_id = session.get('faculty_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Teams mentored
    cursor.execute("""
        SELECT 
            t.Team_ID,
            GROUP_CONCAT(s.Name SEPARATOR ', ') AS Members,
            p.Title AS ProjectTitle,
            p.Status AS ProjectStatus
        FROM Team t
        LEFT JOIN Team_Student ts ON t.Team_ID = ts.Team_ID
        LEFT JOIN Student s ON ts.SRN = s.SRN
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE t.Faculty_ID = %s
        GROUP BY t.Team_ID, p.Title, p.Status
    """, (faculty_id,))
    teams = cursor.fetchall()

    # Upcoming meetings (DateTime column)
    cursor.execute("""
        SELECT m.Meeting_ID, t.Team_ID, p.Title AS ProjectTitle, m.DateTime, m.Feedback
        FROM Meeting m
        JOIN Team t ON m.Team_ID = t.Team_ID
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE t.Faculty_ID = %s AND m.DateTime >= NOW()
        ORDER BY m.DateTime ASC
    """, (faculty_id,))
    upcoming_meetings = cursor.fetchall()

    # Past meetings
    cursor.execute("""
        SELECT m.Meeting_ID, t.Team_ID, p.Title AS ProjectTitle, m.DateTime, m.Feedback
        FROM Meeting m
        JOIN Team t ON m.Team_ID = t.Team_ID
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE t.Faculty_ID = %s AND m.DateTime < NOW()
        ORDER BY m.DateTime DESC
    """, (faculty_id,))
    past_meetings = cursor.fetchall()

    # Reviews created by this faculty (where team belongs to them)
    cursor.execute("""
        SELECT r.Review_ID, r.ReviewType_ID, t.Team_ID, p.Title AS ProjectTitle, r.Date, r.Venue
        FROM Review r
        JOIN Team t ON r.Team_ID = t.Team_ID
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE t.Faculty_ID = %s
        ORDER BY r.Date DESC
    """, (faculty_id,))
    reviews = cursor.fetchall()

    # Panel reviews where faculty is part of review panel
    cursor.execute("""
        SELECT r.Review_ID, r.Team_ID, p.Title AS ProjectTitle, r.Date, r.Venue
        FROM Review r
        JOIN Review_Panel rp ON r.Review_ID = rp.Review_ID
        LEFT JOIN Team_Project tp ON r.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE rp.Faculty_ID = %s
        ORDER BY r.Date DESC
    """, (faculty_id,))
    panel_reviews = cursor.fetchall()

    # unassigned teams
    cursor.execute("SELECT Team_ID FROM Team WHERE Faculty_ID IS NULL")
    unassigned_teams = cursor.fetchall()

    # Fetch all rubrics
    cursor.execute("SELECT Rubric_ID, Rubric_Name, Max_Marks FROM Rubric")
    rubrics = cursor.fetchall()

    # Fetch all evaluations submitted by this faculty
    cursor.execute("""
        SELECT 
            e.Evaluation_ID,
            e.Review_ID,
            e.SRN,
            s.Name AS StudentName,
            r.Rubric_Name AS RubricName,
            e.Marks,
            e.Comments,
            e.Created_At
            FROM Evaluation e
            JOIN Student s ON e.SRN = s.SRN
            JOIN Rubric r ON e.Rubric_ID = r.Rubric_ID
            WHERE e.Faculty_ID = %s
            ORDER BY e.Created_At DESC;
    """, (faculty_id,))
    evaluations = cursor.fetchall()

    grouped_evals = defaultdict(lambda: defaultdict(list))
    for ev in evaluations:
        grouped_evals[ev['Review_ID']][ev['SRN']].append(ev)

    cursor.close()
    conn.close()

    return render_template(
        'faculty_dashboard.html',
        teams=teams,
        faculty_id=faculty_id,
        upcoming_meetings=upcoming_meetings,
        past_meetings=past_meetings,
        reviews=reviews,
        panel_reviews=panel_reviews,
        unassigned_teams=unassigned_teams,
        rubrics=rubrics,
        grouped_evals=grouped_evals
    )

@app.route('/faculty/schedule_meeting', methods=['POST'])
def faculty_schedule_meeting():
    if session.get('role') != 'faculty':
        flash("Access denied", "danger")
        return redirect(url_for('login'))
    
    faculty_id = request.form.get('faculty_id')
    team_id = request.form.get('team_id')
    datetime = request.form.get('datetime')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Meeting (Faculty_ID, Team_ID, DateTime, Feedback) VALUES (%s, %s, %s, NULL)",
            (faculty_id, team_id, datetime)
        )
        conn.commit()
        flash("Meeting scheduled successfully!", "success")
    except Error as e:
        flash("Error scheduling meeting: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/add_feedback', methods=['POST'])
def faculty_add_feedback():
    if session.get('role') != 'faculty':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    meeting_id = request.form.get('meeting_id')
    feedback = request.form.get('feedback')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Meeting SET Feedback = %s WHERE Meeting_ID = %s", (feedback, meeting_id))
        conn.commit()
        flash("Feedback updated successfully!", "success")
    except Error as e:
        flash("Error updating feedback: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/get_students_by_review/<int:review_id>')
def faculty_get_students_by_review(review_id):
    if session.get('role') != 'faculty':
        return jsonify([])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.SRN, s.Name
        FROM Student s
        JOIN Team_Student ts ON s.SRN = ts.SRN
        JOIN Review r ON ts.Team_ID = r.Team_ID
        WHERE r.Review_ID = %s
    """, (review_id,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)


@app.route('/faculty/evaluate_student', methods=['POST'])
def faculty_evaluate_student():
    if session.get('role') != 'faculty':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    faculty_id = session.get('faculty_id')
    student_srn = request.form.get('student_srn')
    review_id = request.form.get('review_id')
    rubric_ids = request.form.getlist('rubric_id[]')
    marks = request.form.getlist('marks[]')
    comments = request.form.getlist('comments[]')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # validate each entry
        for i in range(len(rubric_ids)):
            rubric_id = rubric_ids[i]
            mark = marks[i]
            comment = comments[i] if comments[i] else None

            cursor.execute("""
                INSERT INTO Evaluation (Faculty_ID, SRN, Rubric_ID, Project_ID, Review_ID, Marks, Comments)
                SELECT %s, %s, %s, tp.Project_ID, %s, %s, %s
                FROM Team_Student ts
                JOIN Team_Project tp ON ts.Team_ID = tp.Team_ID
                WHERE ts.SRN = %s
                ON DUPLICATE KEY UPDATE
                    Marks = VALUES(Marks),
                    Comments = VALUES(Comments)
            """, (faculty_id, student_srn, rubric_id, review_id, mark, comment, student_srn))

        conn.commit()
        flash("Evaluation submitted successfully", "success")
    except Error as e:
        flash(f"Error submitting evaluation: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('faculty_dashboard'))



@app.route('/faculty/claim_team', methods=['POST'])
def faculty_claim_team():
    if session.get('role') != 'faculty':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    team_id = request.form.get('team_id')
    faculty_id = session.get('faculty_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Team SET Faculty_ID = %s WHERE Team_ID = %s AND Faculty_ID IS NULL", (faculty_id, team_id))
        conn.commit()
        if cursor.rowcount:
            flash("Team claimed", "success")
        else:
            flash("Team already assigned", "warning")
    except Error as e:
        flash("Error claiming team: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('faculty_dashboard'))

# -----------------------------
# Student routes
# -----------------------------
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    srn = session.get('srn')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Student info
    cursor.execute("""
        SELECT s.SRN, s.Name AS StudentName, t.Team_ID, f.Name AS FacultyName,
               p.Title AS ProjectTitle, p.Status AS ProjectStatus, p.Description AS ProjectDescription
        FROM Student s
        LEFT JOIN Team_Student ts ON s.SRN = ts.SRN
        LEFT JOIN Team t ON ts.Team_ID = t.Team_ID
        LEFT JOIN Faculty f ON t.Faculty_ID = f.Faculty_ID
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        WHERE s.SRN = %s
        LIMIT 1
    """, (srn,))
    student_info = cursor.fetchone()

    # ✅ Team members
    team_members = []
    meetings = []
    if student_info and student_info.get('Team_ID'):
        cursor.execute("""
            SELECT s.Name, s.SRN 
            FROM Team_Student ts 
            JOIN Student s ON ts.SRN = s.SRN 
            WHERE ts.Team_ID = %s
        """, (student_info['Team_ID'],))
        team_members = cursor.fetchall()

        # ✅ Meetings
        cursor.execute("""
            SELECT m.Meeting_ID, m.DateTime, m.Feedback, f.Name AS FacultyName
            FROM Meeting m
            LEFT JOIN Faculty f ON m.Faculty_ID = f.Faculty_ID
            WHERE m.Team_ID = %s
            ORDER BY m.DateTime DESC
        """, (student_info['Team_ID'],))
        meetings = cursor.fetchall()

    # ✅ Evaluations (no Evaluation_Date)
    cursor.execute("""
        SELECT e.Marks AS Score, f.Name AS FacultyName, e.Comments, e.Project_ID, e.Review_ID
        FROM Evaluation e
        LEFT JOIN Faculty f ON e.Faculty_ID = f.Faculty_ID
        WHERE e.SRN = %s
    """, (srn,))
    evaluations = cursor.fetchall()

     # ---- Review-wise total marks computation ----
    cursor.execute("""
        SELECT 
            rt.Review_Name AS ReviewType,
            r.Review_ID,
            ROUND(SUM(avg_marks),2) AS TotalMarks,
            ROUND(SUM(MaxTotal),2) AS MaxMarks
        FROM (
            SELECT 
                e.Review_ID,
                e.Rubric_ID,
                AVG(e.Marks) AS avg_marks,
                r2.Max_Marks AS MaxTotal
            FROM Evaluation e
            JOIN Rubric r2 ON e.Rubric_ID = r2.Rubric_ID
            WHERE e.SRN = %s
            GROUP BY e.Review_ID, e.Rubric_ID
        ) sub
        JOIN Review r ON r.Review_ID = sub.Review_ID
        JOIN Review_Type rt ON rt.ReviewType_ID = r.ReviewType_ID
        GROUP BY rt.Review_Name, r.Review_ID
        ORDER BY r.Review_ID;
    """, (srn,))
    review_totals = cursor.fetchall()

    # ✅ Upcoming reviews
    upcoming_reviews = []
    if student_info and student_info.get('Team_ID'):
        cursor.execute("""
            SELECT r.Review_ID, r.ReviewType_ID, r.Date, r.Venue,
                   GROUP_CONCAT(CONCAT(f.Faculty_ID, ' - ', f.Name) SEPARATOR '; ') AS FacultyPanel
            FROM Review r
            LEFT JOIN Review_Panel rp ON r.Review_ID = rp.Review_ID
            LEFT JOIN Faculty f ON rp.Faculty_ID = f.Faculty_ID
            WHERE r.Team_ID = %s AND r.Date >= CURDATE()
            GROUP BY r.Review_ID
            ORDER BY r.Date ASC
        """, (student_info['Team_ID'],))
        upcoming_reviews = cursor.fetchall()

    cursor.execute("""
        SELECT Team_ID FROM Team_Student WHERE SRN = %s
    """, (srn,))
    team_info = cursor.fetchone()

    is_in_team = bool(team_info)
    team_id = team_info["Team_ID"] if team_info else None

    if team_info:

        # Check if that team has a project assigned
        cursor.execute("SELECT Project_ID FROM Team_Project WHERE Team_ID = %s", (team_id,))
        project_row = cursor.fetchone()
        has_project = bool(project_row)

    # If in a team, fetch current team members
    team_members = []
    if is_in_team:
        cursor.execute("""
            SELECT s.SRN, s.Name 
            FROM Student s
            JOIN Team_Student ts ON s.SRN = ts.SRN
            WHERE ts.Team_ID = %s
        """, (team_id,))
        team_members = cursor.fetchall()

    # Fetch joinable teams (only if student not in a team)
    available_teams = []
    if not is_in_team:
        cursor.execute("""
            SELECT t.Team_ID, COUNT(ts.SRN) AS member_count
            FROM Team t
            LEFT JOIN Team_Student ts ON t.Team_ID = ts.Team_ID
            GROUP BY t.Team_ID
            HAVING member_count < 4
        """)
        available_teams = cursor.fetchall()


    cursor.close()
    conn.close()

    return render_template('student_dashboard.html',
                           student=student_info,
                           team_members=team_members,
                           meetings=meetings,
                           evaluations=evaluations,
                           upcoming_reviews=upcoming_reviews,
                           is_in_team=is_in_team,
                           has_project=has_project,
                           available_teams=available_teams,
                           review_totals=review_totals)


@app.route('/student/add_teammate', methods=['POST'])
def add_teammate():
    if session.get('role') != 'student':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    srn = request.form.get('srn')
    teammate_srn = request.form.get('teammate_srn')
    join_team_id = request.form.get('join_team_id')  # Optional hidden field when joining existing team

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch current student
        cursor.execute("SELECT SRN, Sem FROM Student WHERE SRN = %s", (srn,))
        student = cursor.fetchone()
        if not student:
            flash("Your record was not found.", "danger")
            return redirect(url_for('student_dashboard'))

        # Check if already in a team
        cursor.execute("SELECT Team_ID FROM Team_Student WHERE SRN = %s", (srn,))
        my_team = cursor.fetchone()

        # Fetch teammate if provided
        teammate = None
        if teammate_srn:
            cursor.execute("SELECT SRN, Sem FROM Student WHERE SRN = %s", (teammate_srn,))
            teammate = cursor.fetchone()
            if not teammate:
                flash("Teammate SRN not found.", "danger")
                return redirect(url_for('student_dashboard'))

            if teammate["Sem"] != student["Sem"]:
                flash("Teammate must be in your semester.", "warning")
                return redirect(url_for('student_dashboard'))

            cursor.execute("SELECT Team_ID FROM Team_Student WHERE SRN = %s", (teammate_srn,))
            their_team = cursor.fetchone()
            if their_team:
                flash("That student is already in another team.", "warning")
                return redirect(url_for('student_dashboard'))

        # CASE 1️⃣: Student already in a team → Add teammate
        if my_team:
            team_id = my_team["Team_ID"]

            cursor.execute("SELECT COUNT(*) AS cnt FROM Team_Student WHERE Team_ID = %s", (team_id,))
            if cursor.fetchone()["cnt"] >= 4:
                flash("Your team already has 4 members.", "warning")
                return redirect(url_for('student_dashboard'))

            if teammate:
                cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (team_id, teammate_srn))
                conn.commit()
                flash(f"{teammate_srn} added to your team!", "success")

        # CASE 2️⃣: Student not in a team → Join existing or create new
        else:
            if join_team_id:
                # Joining an existing team
                cursor.execute("SELECT COUNT(*) AS cnt FROM Team_Student WHERE Team_ID = %s", (join_team_id,))
                count = cursor.fetchone()["cnt"]
                if count >= 4:
                    flash("That team is already full (4 members).", "warning")
                    return redirect(url_for('student_dashboard'))

                cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (join_team_id, srn))
                conn.commit()
                flash("You have successfully joined the team!", "success")

            else:
                # Creating new team
                cursor.execute("INSERT INTO Team (Faculty_ID) VALUES (NULL)")
                team_id = cursor.lastrowid
                cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (team_id, srn))

                # Optionally add teammate if given
                if teammate:
                    cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (team_id, teammate_srn))

                conn.commit()
                flash("New team created successfully!", "success")

    except Error as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('student_dashboard'))



@app.route('/student/add_project', methods=['POST'])
def add_project():
    if session.get('role') != 'student':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    srn = request.form.get('srn')
    title = request.form.get('title')
    description = request.form.get('description', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # insert project
        cursor.execute("INSERT INTO Project (Title, Description, Status) VALUES (%s, %s, %s)",
                       (title, description, 'Ongoing'))
        project_id = cursor.lastrowid

        # find student's team
        cursor.execute("SELECT Team_ID FROM Team_Student WHERE SRN = %s LIMIT 1", (srn,))
        row = cursor.fetchone()
        if row:
            team_id = row[0]
            # map team to project
            cursor.execute("INSERT INTO Team_Project (Team_ID, Project_ID) VALUES (%s, %s)", (team_id, project_id))
            conn.commit()
            flash("Project added & assigned to your team", "success")
        else:
            conn.commit()
            flash("Project added but you're not in a team - please create or join a team", "warning")
    except Error as e:
        flash("Error adding project: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('student_dashboard'))

# -----------------------------
# Admin routes (full management)
# -----------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total_students FROM Student")
    total_students = cursor.fetchone()['total_students']
    cursor.execute("SELECT COUNT(*) AS total_faculty FROM Faculty")
    total_faculty = cursor.fetchone()['total_faculty']
    cursor.execute("SELECT COUNT(*) AS total_projects FROM Project")
    total_projects = cursor.fetchone()['total_projects']
    cursor.execute("SELECT COUNT(*) AS total_teams FROM Team")
    total_teams = cursor.fetchone()['total_teams']
    cursor.execute("SELECT COUNT(*) AS total_reviews FROM Review")
    total_reviews = cursor.fetchone()['total_reviews']

    cursor.execute("SELECT * FROM Student ORDER BY Name")
    students = cursor.fetchall()
    # Fetch all faculty with teams they mentor
    cursor.execute("""
        SELECT f.Faculty_ID, f.Name, f.Email,
            GROUP_CONCAT(t.Team_ID ORDER BY t.Team_ID SEPARATOR ', ') AS TeamIDs
        FROM Faculty f
        LEFT JOIN Team t ON f.Faculty_ID = t.Faculty_ID
        GROUP BY f.Faculty_ID
        ORDER BY f.Faculty_ID
    """)
    faculty = cursor.fetchall()

    cursor.execute("""
        SELECT pr.Project_ID, pr.Title, pr.Status, pr.Description, tp.Team_ID
        FROM Project pr
        LEFT JOIN Team_Project tp ON pr.Project_ID = tp.Project_ID
        ORDER BY pr.Title
    """)
    projects = cursor.fetchall()
    cursor.execute("""
        SELECT t.Team_ID, t.Faculty_ID, GROUP_CONCAT(s.Name SEPARATOR ', ') AS Members
        FROM Team t
        LEFT JOIN Team_Student ts ON t.Team_ID = ts.Team_ID
        LEFT JOIN Student s ON ts.SRN = s.SRN
        GROUP BY t.Team_ID, t.Faculty_ID
        ORDER BY t.Team_ID
    """)
    teams = cursor.fetchall()

    # Fetch unassigned students (not in any team)
    cursor.execute("""
        SELECT s.SRN, s.Name, s.Sem
        FROM Student s
        LEFT JOIN Team_Student ts ON s.SRN = ts.SRN
        WHERE ts.Team_ID IS NULL
        ORDER BY s.Sem, s.SRN
    """)
    unassigned_students = cursor.fetchall()

    # Fetch teams that don't have a project assigned
    cursor.execute("""
        SELECT t.Team_ID
        FROM Team t
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        WHERE tp.Project_ID IS NULL
        ORDER BY t.Team_ID
    """)
    unassigned_teams = cursor.fetchall()

    # Fetch all reviews with team, review type, faculty panel, date, and marks
    cursor.execute("""
        SELECT 
            r.Review_ID,
            rt.Review_Name AS ReviewType,
            r.Date,
            r.Venue,
            GROUP_CONCAT(DISTINCT rp.Faculty_ID ORDER BY rp.Faculty_ID ASC) AS FacultyPanel,
            t.Team_ID,
            p.Title AS ProjectTitle
        FROM Review r
        LEFT JOIN Review_Type rt ON r.ReviewType_ID = rt.ReviewType_ID
        LEFT JOIN Review_Panel rp ON r.Review_ID = rp.Review_ID
        LEFT JOIN Team t ON r.Team_ID = t.Team_ID
        LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
        LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
        GROUP BY r.Review_ID, rt.Review_Name, r.Date, r.Venue, t.Team_ID, p.Title
        ORDER BY r.Date DESC;
    """)
    reviews = cursor.fetchall()

    # Fetch review types for the dropdown
    cursor.execute("SELECT * FROM Review_Type")
    review_types = cursor.fetchall()


    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html',
                           totals={
                               'students': total_students,
                               'faculty': total_faculty,
                               'projects': total_projects,
                               'teams': total_teams,
                               'reviews': total_reviews
                           },
                           students=students,
                           faculty=faculty,
                           projects=projects,
                           teams=teams,
                           unassigned_students=unassigned_students,
                           unassigned_teams=unassigned_teams,
                           reviews=reviews,
                           review_types=review_types)

@app.route('/admin/add_student', methods=['POST'])
def admin_add_student():
    if session.get('role') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))
    
    srn = request.form.get('srn')
    name = request.form.get('name')
    email = request.form.get('email')
    sem = request.form.get('sem')

    # Validate sem before insert
    try:
        sem = int(sem)
        if sem < 1 or sem > 8:
            flash("Semester must be between 1 and 8", "warning")
            return redirect(url_for('admin_dashboard'))
    except (TypeError, ValueError):
        flash("Invalid semester value", "danger")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Student (SRN, Name, Email, Sem) VALUES (%s, %s, %s, %s)",
            (srn, name, email, sem)
        )
        conn.commit()
        flash("Student added successfully", "success")
    except Error as e:
        flash("Error adding student: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_student', methods=['POST'])
def admin_edit_student():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    srn = request.form.get('srn'); name = request.form.get('name'); email = request.form.get('email')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Student SET Name=%s, Email=%s WHERE SRN=%s", (name, email, srn))
        conn.commit(); flash("Student updated", "success")
    except Error as e:
        flash("Error updating student: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_student', methods=['POST'])
def admin_delete_student():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    srn = request.form.get('srn')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Team_Student WHERE SRN = %s", (srn,))
        cursor.execute("DELETE FROM Evaluation WHERE SRN = %s", (srn,))
        cursor.execute("DELETE FROM Student WHERE SRN = %s", (srn,))
        conn.commit(); flash("Student deleted", "success")
    except Error as e:
        flash("Error deleting student: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_faculty', methods=['POST'])
def admin_add_faculty():
    if session.get('role') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    faculty_id = request.form.get('faculty_id')
    name = request.form.get('name')
    email = request.form.get('email')

    # Validate inputs
    if not faculty_id or not faculty_id.isdigit():
        flash("Invalid Faculty ID", "warning")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Faculty (Faculty_ID, Name, Email) VALUES (%s, %s, %s)",
            (faculty_id, name, email)
        )
        conn.commit()
        flash("Faculty added successfully", "success")
    except Error as e:
        flash("Error adding faculty: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_faculty', methods=['POST'])
def admin_edit_faculty():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    fid = request.form.get('faculty_id'); name = request.form.get('name'); email = request.form.get('email')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Faculty SET Name=%s, Email=%s WHERE Faculty_ID=%s", (name, email, fid))
        conn.commit(); flash("Faculty updated", "success")
    except Error as e:
        flash("Error updating faculty: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_faculty', methods=['POST'])
def admin_delete_faculty():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    fid = request.form.get('faculty_id')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Team SET Faculty_ID = NULL WHERE Faculty_ID = %s", (fid,))
        cursor.execute("DELETE FROM Review_Panel WHERE Faculty_ID = %s", (fid,))
        cursor.execute("DELETE FROM Faculty WHERE Faculty_ID = %s", (fid,))
        conn.commit(); flash("Faculty removed", "success")
    except Error as e:
        flash("Error deleting faculty: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_add_project', methods=['POST'])
def admin_add_project():
    if session.get('role') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    title = request.form.get('title')
    status = request.form.get('status', 'Ongoing')
    description = request.form.get('description')
    team_id = request.form.get('team_id')

    if not team_id:
        flash("Please select a team to assign the project.", "warning")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if team already has a project
        cursor.execute("SELECT Project_ID FROM Team_Project WHERE Team_ID = %s", (team_id,))
        existing = cursor.fetchone()
        if existing:
            flash(f"Team {team_id} already has a project assigned (Project ID: {existing['Project_ID']}).", "warning")
            return redirect(url_for('admin_dashboard'))

        # Insert into Project table
        cursor.execute("""
            INSERT INTO Project (Title, Description, Status)
            VALUES (%s, %s, %s)
        """, (title, description, status))
        project_id = cursor.lastrowid

        # Link to Team
        cursor.execute("""
            INSERT INTO Team_Project (Team_ID, Project_ID)
            VALUES (%s, %s)
        """, (team_id, project_id))

        conn.commit()
        flash(f"Project '{title}' added and assigned to Team {team_id}.", "success")

    except Error as e:
        conn.rollback()
        flash(f"Error adding project: {e}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_project', methods=['POST'])
def admin_edit_project():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    pid = request.form.get('project_id'); title = request.form.get('title'); desc = request.form.get('description',''); status = request.form.get('status','Ongoing')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Project SET Title=%s, Description=%s, Status=%s WHERE Project_ID=%s", (title, desc, status, pid))
        conn.commit(); flash("Project updated", "success")
    except Error as e:
        flash("Error updating project: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_project', methods=['POST'])
def admin_delete_project():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    pid = request.form.get('project_id')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Team_Project WHERE Project_ID = %s", (pid,))
        cursor.execute("DELETE FROM Evaluation WHERE Project_ID = %s", (pid,))
        cursor.execute("DELETE FROM Project WHERE Project_ID = %s", (pid,))
        conn.commit(); flash("Project deleted", "success")
    except Error as e:
        flash("Error deleting project: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_add_team', methods=['POST'])
def admin_add_team():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    faculty_id = request.form.get('faculty_id') or None
    student_srns = request.form.getlist('student_srns')  # because <select multiple>

    if not student_srns or len(student_srns) == 0:
        flash("Select at least one student to form a team.", "warning")
        return redirect(url_for('admin_dashboard'))

    if len(student_srns) > 4:
        flash("A team cannot have more than 4 members.", "warning")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Validate students are still unassigned (no race condition)
        cursor.execute("""
            SELECT SRN FROM Team_Student WHERE SRN IN (%s)
        """ % ','.join(['%s'] * len(student_srns)), tuple(student_srns))
        already_assigned = [row['SRN'] for row in cursor.fetchall()]

        if already_assigned:
            flash(f"Cannot create team. These students are already assigned to a team: {', '.join(already_assigned)}", "danger")
            return redirect(url_for('admin_dashboard'))

        # Create team
        if faculty_id:
            cursor.execute("INSERT INTO Team (Faculty_ID) VALUES (%s)", (faculty_id,))
        else:
            cursor.execute("INSERT INTO Team (Faculty_ID) VALUES (NULL)")
        team_id = cursor.lastrowid

        # Add students to Team_Student
        for srn in student_srns:
            cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (team_id, srn))

        conn.commit()
        flash(f"Team {team_id} created successfully with {len(student_srns)} member(s).", "success")

    except Error as e:
        conn.rollback()
        flash("Error creating team: " + str(e), "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin_add_team_member', methods=['POST'])
def admin_add_team_member():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    team_id = request.form.get('team_id')
    srn = request.form.get('srn')

    if not team_id or not srn:
        flash("Team and student are required.", "warning")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if team already has 4 members
        cursor.execute("SELECT COUNT(*) AS cnt FROM Team_Student WHERE Team_ID = %s", (team_id,))
        count = cursor.fetchone()['cnt']
        if count >= 4:
            flash(f"Team {team_id} already has 4 members. Cannot add more.", "warning")
            return redirect(url_for('admin_dashboard'))

        # Check if student already belongs to a team
        cursor.execute("SELECT Team_ID FROM Team_Student WHERE SRN = %s", (srn,))
        existing = cursor.fetchone()
        if existing:
            flash(f"Student {srn} already belongs to Team {existing['Team_ID']}.", "danger")
            return redirect(url_for('admin_dashboard'))

        # Add student
        cursor.execute("INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)", (team_id, srn))
        conn.commit()
        flash(f"Student {srn} added to Team {team_id}.", "success")

    except Error as e:
        conn.rollback()
        flash("Error adding team member: " + str(e), "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin_remove_team_member', methods=['POST'])
def admin_remove_team_member():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    team_id = request.form.get('team_id')
    srn = request.form.get('srn')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Team_Student WHERE Team_ID = %s AND SRN = %s", (team_id, srn))
        conn.commit()
        flash(f"Student {srn} removed from Team {team_id}.", "success")
    except Error as e:
        conn.rollback()
        flash("Error removing team member: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_team', methods=['POST'])
def admin_delete_team():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    tid = request.form.get('team_id')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Team_Student WHERE Team_ID = %s", (tid,))
        cursor.execute("DELETE FROM Team_Project WHERE Team_ID = %s", (tid,))
        cursor.execute("DELETE FROM Team WHERE Team_ID = %s", (tid,))
        conn.commit(); flash("Team deleted", "success")
    except Error as e:
        flash("Error deleting team: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_faculty', methods=['POST'])
def admin_assign_faculty():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    team_id = request.form.get('team_id'); fid = request.form.get('faculty_id')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Team SET Faculty_ID = %s WHERE Team_ID = %s", (fid, team_id))
        conn.commit(); flash("Faculty assigned", "success")
    except Error as e:
        flash("Error assigning faculty: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_project', methods=['POST'])
def admin_assign_project():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    team_id = request.form.get('team_id'); project_id = request.form.get('project_id')
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Team_Project WHERE Team_ID = %s", (team_id,))
        cursor.execute("INSERT INTO Team_Project (Team_ID, Project_ID) VALUES (%s, %s)", (team_id, project_id))
        conn.commit(); flash("Project assigned", "success")
    except Error as e:
        flash("Error assigning project: " + str(e), "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_edit_review', methods=['POST'])
def admin_edit_review():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    review_id = request.form.get('review_id')
    date = request.form.get('date')
    venue = request.form.get('venue')
    panel_faculty_ids = request.form.get('panel_faculty_ids', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update review details
        cursor.execute("UPDATE Review SET Date=%s, Venue=%s WHERE Review_ID=%s", (date, venue, review_id))

        # Update panel assignments
        cursor.execute("DELETE FROM Review_Panel WHERE Review_ID=%s", (review_id,))
        if panel_faculty_ids.strip():
            ids = [fid.strip() for fid in panel_faculty_ids.split(',') if fid.strip()]
            for fid in ids:
                cursor.execute("INSERT INTO Review_Panel (Review_ID, Faculty_ID) VALUES (%s, %s)", (review_id, fid))

        conn.commit()
        flash(f"Review {review_id} updated successfully.", "success")

    except Error as e:
        conn.rollback()
        flash("Error updating review: " + str(e), "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin_delete_review', methods=['POST'])
def admin_delete_review():
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    review_id = request.form.get('review_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Review_Panel WHERE Review_ID=%s", (review_id,))
        cursor.execute("DELETE FROM Evaluation WHERE Review_ID=%s", (review_id,))
        cursor.execute("DELETE FROM Review WHERE Review_ID=%s", (review_id,))
        conn.commit()
        flash(f"Review {review_id} deleted successfully.", "success")

    except Error as e:
        conn.rollback()
        flash("Error deleting review: " + str(e), "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/schedule_review', methods=['POST'])
def admin_schedule_review():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    team_id = request.form.get('team_id')
    review_type_id = request.form.get('review_type_id')
    date = request.form.get('date')
    venue = request.form.get('venue')
    panel_faculty_ids = request.form.get('panel_faculty_ids', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert into Review table
        cursor.execute("""
            INSERT INTO Review (ReviewType_ID, Team_ID, Date, Venue)
            VALUES (%s, %s, %s, %s)
        """, (review_type_id, team_id, date, venue))
        review_id = cursor.lastrowid

        # Build panel faculty list (mentor + additional)
        # Get mentor from Team
        cursor.execute("SELECT Faculty_ID FROM Team WHERE Team_ID = %s", (team_id,))
        mentor_row = cursor.fetchone()
        mentor_id = mentor_row[0] if mentor_row and mentor_row[0] else None

        faculty_ids = set()
        if panel_faculty_ids:
            faculty_ids.update(fid.strip() for fid in panel_faculty_ids.split(',') if fid.strip())
        if mentor_id:
            faculty_ids.add(str(mentor_id))

        # Insert each faculty into Review_Panel
        for fid in faculty_ids:
            cursor.execute("INSERT INTO Review_Panel (Review_ID, Faculty_ID) VALUES (%s, %s)", (review_id, fid))

        conn.commit()
        flash(f"Review scheduled successfully for Team {team_id}.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error scheduling review: {e}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/get_review_details/<int:review_id>')
def admin_get_review_details(review_id):
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            e.Evaluation_ID,
            s.SRN,
            s.Name AS StudentName,
            r.Rubric_Name,
            e.Marks,
            e.Comments,
            f.Name AS FacultyName,
            e.Created_At
        FROM Evaluation e
        JOIN Student s ON e.SRN = s.SRN
        JOIN Rubric r ON e.Rubric_ID = r.Rubric_ID
        JOIN Faculty f ON e.Faculty_ID = f.Faculty_ID
        WHERE e.Review_ID = %s
        ORDER BY s.SRN, r.Rubric_Name;
    """, (review_id,))

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)


@app.route('/admin/get_students')
def admin_get_students():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student ORDER BY Name")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)

# -----------------------------
# Error handlers (optional)
# -----------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# -----------------------------
# Run
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
