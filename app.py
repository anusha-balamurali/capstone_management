# This is the "bridge" (API) that connects your frontend to the database.
# This version includes new endpoints for specific user roles.

from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error, errorcode
from flask_cors import CORS
from decimal import Decimal # Import Decimal for handling potential decimal results
import datetime # Import datetime to handle DATE objects

# --- 1. SETUP ---
app = Flask(__name__)
CORS(app) # Allow frontend requests

# --- 2. DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345', # <-- IMPORTANT: SET YOUR MYSQL PASSWORD
    'database': 'capstoneprojectdb'
}

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        # print("DB Connection Successful") # Debug log
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# --- Helper function to handle Decimal and Date conversion for JSON ---
#
# THIS IS THE FIX FOR "Error loading projects"
#
def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (Decimal)):
        # Convert Decimal to float for JSON
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        # Convert Date/Datetime objects to ISO 8601 string
        return obj.isoformat()
    # If it's not a type we handle, raise TypeError so json.dumps fails clearly
    raise TypeError(f"Type {type(obj)} not serializable")


# --- Helper function for database errors ---
def handle_db_error(e):
    """Returns a standardized error message from a DB exception."""
    print(f"Database Error: {e}")
    # Check for custom trigger errors (SQLSTATE 45000)
    if hasattr(e, 'sqlstate') and e.sqlstate == '45000':
         # Attempt to extract the custom message if available
        msg = getattr(e, 'msg', 'A database rule was violated.') 
        return jsonify({"error": msg}), 400
    # Handle other potential errors like connection issues, syntax errors, etc.
    return jsonify({"error": f"An unexpected database error occurred: {str(e)}"}), 500


# --- 3. API ENDPOINTS ---

@app.route('/')
def home():
    return "Capstone API Server is running!"

# --- GET Endpoints (Read Data) ---

@app.route('/api/students', methods=['GET'])
def get_students():
    """Gets basic student info for dropdowns."""
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT SRN, Name FROM Student ORDER BY Name")
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(students)
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/faculty', methods=['GET'])
def get_faculty():
    """Gets basic faculty info for dropdowns."""
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Faculty_ID, Name FROM Faculty ORDER BY Name")
        faculty = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(faculty)
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Gets teams with mentor and student info, using the view."""
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        
        # Use the Team_Student_View logic adapted slightly
        cursor.execute("""
            SELECT 
                t.Team_ID, 
                t.Faculty_ID AS Mentor_ID, 
                f.Name AS Mentor_Name,
                GROUP_CONCAT(DISTINCT CONCAT(s.Name, ' (', s.SRN, ')') ORDER BY s.Name SEPARATOR '; ') AS Students_Concat
            FROM Team t
            JOIN Faculty f ON t.Faculty_ID = f.Faculty_ID
            LEFT JOIN Team_Student ts ON t.Team_ID = ts.Team_ID
            LEFT JOIN Student s ON ts.SRN = s.SRN
            GROUP BY t.Team_ID, t.Faculty_ID, f.Name
            ORDER BY t.Team_ID
        """)
        
        teams_raw = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Process the concatenated student string into a list
        teams_processed = []
        for team in teams_raw:
            students_list = []
            if team.get('Students_Concat'):
                # Split by '; ' and filter out potential empty strings if any student has no name/SRN
                students_list = [s.strip() for s in team['Students_Concat'].split(';') if s.strip()]
            
            teams_processed.append({
                "Team_ID": team['Team_ID'],
                "Mentor_ID": team['Mentor_ID'],
                "Mentor_Name": team['Mentor_Name'],
                "Students": students_list # Keep the key name simple
            })
            
        return jsonify(teams_processed)
    except Error as e:
        print(f"Error fetching teams: {e}")
        return jsonify({"error": f"Database error fetching teams: {e}"}), 500
    except Exception as e:
         print(f"Unexpected error fetching teams: {e}")
         return jsonify({"error": f"Server error processing teams: {e}"}), 500


# --- Dashboard Endpoints ---

@app.route('/api/dashboard/admin-view', methods=['GET'])
def get_admin_dashboard():
    """Gets combined project/review info using the Admin_View."""
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Admin_View ORDER BY Project_ID, Review_ID")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        # Use json.dumps with the CORRECT handler
        import json
        return app.response_class(
            response=json.dumps(data, default=json_serializer, indent=4), # <-- USES THE NEW HELPER
            status=200,
            mimetype='application/json'
        )
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/faculty/<int:faculty_id>/dashboard', methods=['GET'])
def get_faculty_dashboard(faculty_id):
    """Gets data specific to a faculty member's dashboard."""
    dashboard_data = {
        "mentored_teams": [],
        "panel_reviews": []
    }
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        # 1. Get teams mentored by this faculty
        cursor.execute("""
            SELECT 
                t.Team_ID, 
                GROUP_CONCAT(DISTINCT s.Name ORDER BY s.Name SEPARATOR ', ') AS Students
            FROM Team t 
            LEFT JOIN Team_Student ts ON t.Team_ID = ts.Team_ID
            LEFT JOIN Student s ON ts.SRN = s.SRN
            WHERE t.Faculty_ID = %s
            GROUP BY t.Team_ID
            ORDER BY t.Team_ID
        """, (faculty_id,))
        dashboard_data["mentored_teams"] = cursor.fetchall()
        # Convert student string to list for consistency
        for team in dashboard_data["mentored_teams"]:
            team["Students"] = team["Students"].split(', ') if team.get("Students") else []


        # 2. Get reviews where this faculty is on the panel
        cursor.execute("""
            SELECT 
                r.Review_ID, rt.Review_Name, r.Date, r.Venue, r.Team_ID, p.Title
            FROM Review_Panel rp
            JOIN Review r ON rp.Review_ID = r.Review_ID
            JOIN Review_Type rt ON r.ReviewType_ID = rt.ReviewType_ID
            LEFT JOIN Team_Project tp ON r.Team_ID = tp.Team_ID 
            LEFT JOIN Project p ON tp.Project_ID = p.Project_ID 
            WHERE rp.Faculty_ID = %s
            ORDER BY r.Date DESC, r.Review_ID
        """, (faculty_id,))
        dashboard_data["panel_reviews"] = cursor.fetchall()

        cursor.close()
        conn.close()
        # Use json.dumps with the CORRECT handler
        import json
        return app.response_class(
            response=json.dumps(dashboard_data, default=json_serializer, indent=4), # <-- USES THE NEW HELPER
            status=200,
            mimetype='application/json'
        )
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/student/<string:srn>/dashboard', methods=['GET'])
def get_student_dashboard(srn):
    """Gets data specific to a student's dashboard."""
    dashboard_data = {
        "team_info": None,
        "evaluations": [],
        "total_marks": 0.0 # Default to float
    }
    conn = None
    cursor = None
    cursor_func = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True) # Use dictionary cursor for most queries

        # 1. Get Team, Project, and Mentor info for the student
        cursor.execute("""
            SELECT 
                t.Team_ID, p.Title AS Project_Title, p.Status AS Project_Status, 
                f.Name AS Mentor_Name,
                (SELECT GROUP_CONCAT(DISTINCT s2.Name ORDER BY s2.Name SEPARATOR ', ') 
                 FROM Team_Student ts2 
                 JOIN Student s2 ON ts2.SRN = s2.SRN 
                 WHERE ts2.Team_ID = t.Team_ID) AS Members
            FROM Student s
            LEFT JOIN Team_Student ts ON s.SRN = ts.SRN
            LEFT JOIN Team t ON ts.Team_ID = t.Team_ID
            LEFT JOIN Faculty f ON t.Faculty_ID = f.Faculty_ID
            LEFT JOIN Team_Project tp ON t.Team_ID = tp.Team_ID
            LEFT JOIN Project p ON tp.Project_ID = p.Project_ID
            WHERE s.SRN = %s
        """, (srn,))
        team_info = cursor.fetchone() 
        if team_info and team_info['Team_ID']: # Check if student is actually in a team
             # Convert Members string to list
             team_info["Members"] = team_info["Members"].split(', ') if team_info.get("Members") else []
             dashboard_data["team_info"] = team_info
        else:
             # If student isn't in a team, set team_info to None (already default)
             print(f"Student {srn} not found in any team.")
             # No need to query evaluations or total marks if not in a team
             cursor.close()
             conn.close()
             return jsonify(dashboard_data) # Return early


        # 2. Get Evaluations for the student (only if they are in a team)
        cursor.execute("""
            SELECT 
                e.Marks, e.Comments, 
                r.Rubric_Name, 
                rt.Review_Name, 
                f.Name AS Faculty_Name,
                rev.Date AS Review_Date,    -- Added Date
                rev.Venue AS Review_Venue   -- Added Venue
            FROM Evaluation e
            JOIN Rubric r ON e.Rubric_ID = r.Rubric_ID
            JOIN Review rev ON e.Review_ID = rev.Review_ID # Added join for Review details
            JOIN Review_Type rt ON rev.ReviewType_ID = rt.ReviewType_ID
            JOIN Faculty f ON e.Faculty_ID = f.Faculty_ID
            WHERE e.SRN = %s
            ORDER BY rev.Date, rt.Review_Name, r.Rubric_Name 
        """, (srn,))
        dashboard_data["evaluations"] = cursor.fetchall()

        # 3. Get Total Marks using the function (only if they are in a team)
        cursor_func = conn.cursor() # Use a separate, standard cursor for function call
        cursor_func.execute("SELECT GetStudentTotalMarks(%s)", (srn,))
        result = cursor_func.fetchone()
        
        # Explicitly handle result and convert Decimal
        if result and result[0] is not None:
             marks_value_func = result[0]
             print(f"SRN: {srn} (Dashboard) - Raw result from DB function: {marks_value_func} (Type: {type(marks_value_func)})")
             try:
                 dashboard_data["total_marks"] = float(marks_value_func)
             except (TypeError, ValueError):
                 print(f"SRN: {srn} (Dashboard) - Error converting function result to float.")
                 dashboard_data["total_marks"] = 0.0 # Fallback
        else:
            print(f"SRN: {srn} (Dashboard) - GetStudentTotalMarks returned NULL or no result.")
            dashboard_data["total_marks"] = 0.0 # Fallback
        
        print(f"SRN: {srn} (Dashboard) - Final total_marks: {dashboard_data['total_marks']}")
        
        # Use json.dumps with the CORRECT handler
        import json
        return app.response_class(
            response=json.dumps(dashboard_data, default=json_serializer, indent=4), # <-- USES THE NEW HELPER
            status=200,
            mimetype='application/json'
        )

    except Error as e:
        print(f"DB Error fetching student dashboard for {srn}: {e.errno} - {e.msg}")
        return jsonify({"error": f"Database error: {e.msg}"}), 500
    except Exception as e:
        import traceback
        print(f"Server Error fetching student dashboard for {srn}: {e}")
        traceback.print_exc() # Print full traceback to server console
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500
    finally:
        # Ensure all cursors and connection are closed
        if cursor: cursor.close()
        if cursor_func: cursor_func.close()
        if conn and conn.is_connected(): conn.close()


# --- POST Endpoints (Write Data) ---

@app.route('/api/team', methods=['POST'])
def create_team():
    """Creates a new team and adds students."""
    data = request.json
    mentor_id = data.get('mentor_id')
    student_srns = data.get('student_srns', []) # Expecting a list of SRNs

    if not mentor_id or not student_srns:
        return jsonify({"error": "Mentor ID and at least one student SRN are required"}), 400
    if len(student_srns) > 4:
        return jsonify({"error": "A team cannot have more than 4 members"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()

        # Check if any student is already in another team
        placeholders = ', '.join(['%s'] * len(student_srns))
        check_sql = f"SELECT SRN FROM Team_Student WHERE SRN IN ({placeholders})"
        cursor.execute(check_sql, tuple(student_srns)) # Pass as tuple
        existing_students = cursor.fetchall()
        if existing_students:
            srns_in_teams = [s[0] for s in existing_students]
            return jsonify({"error": f"Students already in a team: {', '.join(srns_in_teams)}"}), 400


        # Start transaction
        conn.start_transaction()

        # 1. Insert into Team table
        cursor.execute("INSERT INTO Team (Faculty_ID) VALUES (%s)", (mentor_id,))
        team_id = cursor.lastrowid 

        # 2. Insert into Team_Student table
        student_data = [(team_id, srn) for srn in student_srns]
        insert_sql = "INSERT INTO Team_Student (Team_ID, SRN) VALUES (%s, %s)"
        cursor.executemany(insert_sql, student_data)

        conn.commit()

        message = f"Team {team_id} created successfully with mentor {mentor_id} and students: {', '.join(student_srns)}"
        return jsonify({"message": message, "team_id": team_id}), 201

    except Error as e:
        if conn and conn.is_connected(): conn.rollback() 
        print(f"Error creating team: {e.errno} - {e.msg}")
        return handle_db_error(e) # Use the helper
    except Exception as e:
         if conn and conn.is_connected(): conn.rollback()
         import traceback
         print(f"Unexpected Python error creating team: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/api/project', methods=['POST'])
def create_project():
    """Creates a new project and assigns it to a team."""
    data = request.json
    title = data.get('title')
    team_id = data.get('team_id')

    if not title or not team_id:
        return jsonify({"error": "Project title and team ID are required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()

        conn.start_transaction()

        # 1. Insert into Project table
        cursor.execute("INSERT INTO Project (Title) VALUES (%s)", (title,))
        project_id = cursor.lastrowid

        # 2. Insert into Team_Project table
        cursor.execute("INSERT INTO Team_Project (Team_ID, Project_ID) VALUES (%s, %s)", (team_id, project_id))

        conn.commit()

        return jsonify({"message": f"Project '{title}' created and assigned to team {team_id}", "project_id": project_id}), 201

    except Error as e:
        if conn and conn.is_connected(): conn.rollback()
        print(f"Error creating project: {e.errno} - {e.msg}")
        # Check for unique constraint violation (team already has a project)
        if e.errno == errorcode.ER_DUP_ENTRY:
             return jsonify({"error": f"Team {team_id} already has a project assigned."}), 400
        return handle_db_error(e) # Use the helper
    except Exception as e:
         if conn and conn.is_connected(): conn.rollback()
         import traceback
         print(f"Unexpected Python error creating project: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/api/review', methods=['POST'])
def add_review():
    """Adds a new review by calling the Stored Procedure."""
    data = request.json
    required_fields = ['rev_type_id', 'team_id', 'rev_date', 'panel_faculty_ids']
    if not all(field in data and data[field] for field in required_fields):
         return jsonify({"error": "Missing required fields for review (type, team, date, panel)"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()

        args = [
            data['rev_type_id'],
            data['team_id'],
            data['rev_date'],
            data.get('venue', None), # Venue is optional
            data['panel_faculty_ids']
        ]

        # Use callproc correctly
        cursor.callproc('AddReviewForTeam', args) 
        conn.commit() # Commit after successful call

        return jsonify({"message": "Review added successfully!"}), 201

    except Error as e:
        # Catch specific trigger/procedure errors based on MESSAGE_TEXT
        print(f"Error adding review (DB): {e.errno} - {e.msg}")
        return handle_db_error(e) # Use the helper
    except Exception as e:
         import traceback
         print(f"Unexpected Python error adding review: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/api/evaluation', methods=['POST'])
def add_evaluation():
    """Adds a new evaluation, firing the check_marks trigger."""
    data = request.json
    required_fields = ['faculty_id', 'srn', 'rubric_id', 'project_id', 'review_id', 'marks']
    if not all(field in data and data[field] is not None for field in required_fields): # Check for None too
         return jsonify({"error": "Missing required fields for evaluation"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()

        sql = """
        INSERT INTO Evaluation 
        (Faculty_ID, SRN, Rubric_ID, Project_ID, Review_ID, Marks, Comments) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        val = (
            data['faculty_id'],
            data['srn'],
            data['rubric_id'],
            data['project_id'],
            data['review_id'],
            data['marks'],
            data.get('comments', None) # Comments optional
        )
        
        cursor.execute(sql, val)
        conn.commit()
        
        return jsonify({"message": "Evaluation submitted successfully!"}), 201

    except Error as e:
        print(f"Error adding evaluation (DB): {e.errno} - {e.msg}")
        #
        # THIS IS THE INDENTATION FIX
        #
        if conn and conn.is_connected(): conn.rollback()
        return handle_db_error(e) # Use the helper
    except Exception as e:
         if conn and conn.is_connected(): conn.rollback()
         import traceback
         print(f"Unexpected Python error adding evaluation: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/api/meeting', methods=['POST'])
def log_meeting():
    """Logs a meeting, firing the check_meeting_mentor trigger."""
    data = request.json
    required_fields = ['faculty_id', 'team_id', 'datetime']
    if not all(field in data and data[field] for field in required_fields):
         return jsonify({"error": "Missing required fields for meeting (faculty, team, datetime)"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()

        sql = """
        INSERT INTO Meeting (Faculty_ID, Team_ID, DateTime, Feedback) 
        VALUES (%s, %s, %s, %s)
        """
        val = (
            data['faculty_id'],
            data['team_id'],
            data['datetime'],
            data.get('feedback', None) # Feedback optional
        )
        
        cursor.execute(sql, val)
        conn.commit()
        
        return jsonify({"message": "Meeting logged successfully!"}), 201

    except Error as e:
        if conn and conn.is_connected(): conn.rollback()
        print(f"Error logging meeting (DB): {e.errno} - {e.msg}")
        return handle_db_error(e) # Use the helper
    except Exception as e:
         if conn and conn.is_connected(): conn.rollback()
         import traceback
         print(f"Unexpected Python error logging meeting: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


# =========================================
# REPORT Endpoints (for Admin)
# =========================================

@app.route('/api/reports/mentor-workload', methods=['GET'])
def get_mentor_workload():
    """Gets data from the Mentor_View."""
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        # Ensure Mentor_View exists and query it
        cursor.execute("SELECT Faculty_ID, Faculty_Name, Team_ID, Team_Size FROM Mentor_View ORDER BY Faculty_Name, Team_ID")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        # Use json.dumps with the CORRECT handler
        import json
        return app.response_class(
            response=json.dumps(data, default=json_serializer, indent=4), # <-- USES THE NEW HELPER
            status=200,
            mimetype='application/json'
        )
    except Error as e:
        print(f"Error fetching mentor workload: {e.errno} - {e.msg}")
         # Check if the view doesn't exist
        if e.errno == errorcode.ER_NO_SUCH_TABLE:
            return jsonify({"error": "Server Error: 'Mentor_View' not found in the database. Please run the SQL setup script."}), 500
        return jsonify({"error": str(e.msg)}), 500
    except Exception as e:
        import traceback
        print(f"Unexpected Python error fetching mentor workload: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {e}"}), 500

#
# THIS IS THE ROUTE THAT WAS CAUSING THE 404
#
@app.route('/api/reports/student-marks/<string:srn>', methods=['GET'])
def get_student_marks(srn):
    """Gets total marks for a student using the GetStudentTotalMarks function."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor() 
        
        # Correctly call the function and fetch the scalar result
        cursor.execute("SELECT GetStudentTotalMarks(%s) AS TotalMarksResult", (srn,))
        result = cursor.fetchone() 
        
        total_marks = 0.0 # Default to float 0.0

        if result and result[0] is not None:
            # The function returns DECIMAL
            marks_value = result[0]
            print(f"SRN: {srn} - Raw result from DB function: {marks_value} (Type: {type(marks_value)})") # Debug raw value
            try:
                # Explicitly convert potential Decimal to float
                total_marks = float(marks_value)
            except (TypeError, ValueError) as conversion_error:
                 print(f"SRN: {srn} - Error converting marks value '{marks_value}' to float: {conversion_error}")
                 pass # Fallback to default 0.0 is already set
        else:
             print(f"SRN: {srn} - No marks found or function returned NULL.") # Log if no result

        print(f"SRN: {srn} - Final total_marks value being returned: {total_marks}") # Log final value

        return jsonify({"TotalMarks": total_marks}) 
        
    except Error as e:
        # Log the detailed database error on the server
        print(f"Database Error in get_student_marks for SRN {srn}: {e.errno} - {e.msg}")
         # Check if the function doesn't exist
        if e.errno == errorcode.ER_SP_DOES_NOT_EXIST:
             return jsonify({"error": "Server Error: 'GetStudentTotalMarks' function not found in the database."}), 500
        return jsonify({"error": f"Database error executing function: {e.msg}"}), 500
    except Exception as e:
        # Catch other unexpected Python errors
        import traceback
        print(f"Unexpected Python error in get_student_marks for SRN {srn}: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server processing error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/api/reports/team-average/<int:team_id>/<int:review_id>', methods=['GET'])
def get_team_average(team_id, review_id):
    """Gets average marks for a team in a review using GetTeamAverageMarks function."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        
        # Correctly call the function
        cursor.execute("SELECT GetTeamAverageMarks(%s, %s) AS AverageMarksResult", (team_id, review_id))
        result = cursor.fetchone()

        avg_marks = 0.0 # Default to float 0.0
        if result and result[0] is not None:
            # Convert Decimal result from DB to float for JSON
             marks_value_avg = result[0]
             print(f"Team: {team_id}, Review: {review_id} - Raw result from DB function: {marks_value_avg} (Type: {type(marks_value_avg)})")
             try:
                avg_marks = float(marks_value_avg)
             except (TypeError, ValueError) as conversion_error:
                 print(f"Team: {team_id}, Review: {review_id} - Error converting avg marks value '{marks_value_avg}' to float: {conversion_error}")
                 pass # Fallback to 0.0
        else:
             print(f"Team: {team_id}, Review: {review_id} - No marks found or function returned NULL.")
        
         # Debugging print on server
        print(f"Team: {team_id}, Review: {review_id} - Final AverageMarks value being returned: {avg_marks}")

        return jsonify({"AverageMarks": avg_marks})

    except Error as e:
        print(f"Database Error in get_team_average for Team {team_id}, Review {review_id}: {e.errno} - {e.msg}")
        if e.errno == errorcode.ER_SP_DOES_NOT_EXIST:
             return jsonify({"error": "Server Error: 'GetTeamAverageMarks' function not found in the database."}), 500
        return jsonify({"error": f"Database error executing function: {e.msg}"}), 500
    except Exception as e:
         import traceback
         print(f"Unexpected Python error in get_team_average for Team {team_id}, Review {review_id}: {e}")
         traceback.print_exc()
         return jsonify({"error": f"Server processing error: {e}"}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# =========================================
# RUN SERVER
# =========================================
if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your network if needed, otherwise 127.0.0.1
    app.run(host='127.0.0.1', port=5000, debug=True)

