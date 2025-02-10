from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = "your_secret_key"
csrf = CSRFProtect(app)

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': 'Nous@12345',  # Replace with your MySQL password
    'database': 'cheating_incident_db'
}

# Initialize MySQL connection
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        usn VARCHAR(50) NOT NULL UNIQUE,
                        email VARCHAR(255) NOT NULL,
                        mobile_number VARCHAR(15) NOT NULL,
                        course VARCHAR(255) NOT NULL,
                        specialization VARCHAR(255),
                        current_year INT NOT NULL,
                        current_sem INT NOT NULL,
                        department VARCHAR(255) NOT NULL,
                        proctor VARCHAR(255) NOT NULL
                    )''')
    conn.commit()
    cursor.close()
    conn.close()

# Home page
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch incidents with the new columns
    cursor.execute('''SELECT students.name, students.usn, incidents.fine_amount, 
                      incidents.meeting_schedule, incidents.status, incidents.exam_name, 
                      incidents.exam_date, incidents.invigilator_name, incidents.squad_name, 
                      incidents.exam_room, incidents.mode_of_cheating 
                      FROM incidents 
                      JOIN students ON incidents.student_id = students.id''')
    incidents = cursor.fetchall()

    # Fetch students for the dropdown
    cursor.execute("SELECT id, name, usn FROM students")
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    # Render the index template with incidents and students data
    return render_template('index.html', incidents=incidents, students=students)


@app.route('/update_status', methods=['POST'])
def update_status():
    # Get data from JSON payload
    data = request.json
    incident_id = data.get('incident_id')
    new_status = data.get('new_status')
    csrf_token = data.get('csrf_token')

    # Debugging: Print received data
    print(f"Received data - Incident ID: {incident_id}, New Status: {new_status}, CSRF Token: {csrf_token}")

    # Check if incident_id and new_status are provided
    if not incident_id or not new_status:
        print("Missing incident_id or new_status in the request.")
        return jsonify({"error": "Missing incident_id or new_status in the request."}), 400

    # CSRF Token validation (you should have a CSRF validation function)
    if not validate_csrf_token(csrf_token):
        print("Invalid CSRF Token.")
        return jsonify({"error": "Invalid CSRF Token."}), 403  # Forbidden if CSRF Token is invalid

    # Database connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Debugging: Print the SQL query
        query = "UPDATE incidents SET status = %s WHERE id = %s"
        print(f"Executing query: {query} with values: ({new_status}, {incident_id})")

        # Update the status of the incident
        cursor.execute(query, (new_status, incident_id))
        conn.commit()
        print("Status updated successfully!")

        return jsonify({"message": "Status updated successfully!"}), 200
    except mysql.connector.Error as err:
        print(f"Error updating status: {err}")
        return jsonify({"error": f"An error occurred: {err}"}), 500
    finally:
        # Clean up the database connection
        cursor.close()
        conn.close()

# Add student
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        usn = request.form['usn']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        course = request.form['course']
        specialization = request.form['specialization']
        current_year = request.form['current_year']
        current_sem = request.form['current_sem']
        department = request.form['department']
        proctor = request.form['proctor']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO students 
                              (name, usn, email, mobile_number, course, specialization, 
                               current_year, current_sem, department, proctor) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (name, usn, email, mobile_number, course, specialization,
                            current_year, current_sem, department, proctor))
            conn.commit()
            flash('Student added successfully!', 'success')
        except mysql.connector.IntegrityError:
            flash('USN already exists!', 'error')
        except mysql.connector.Error as err:
            flash(f'An error occurred: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        #return redirect(url_for('index'))
    return render_template('add_student.html')

# Admin dashboard
@app.route('/admin')
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch incidents with the new columns
    cursor.execute('''SELECT students.name, students.usn, incidents.fine_amount, 
                      incidents.meeting_schedule, incidents.status, incidents.exam_name, 
                      incidents.exam_date, incidents.invigilator_name, incidents.squad_name, 
                      incidents.exam_room, incidents.mode_of_cheating 
                      FROM incidents 
                      JOIN students ON incidents.student_id = students.id''')
    incidents = cursor.fetchall()

    # Fetch students for the dropdown
    cursor.execute("SELECT id, name, usn FROM students")
    students = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin.html', incidents=incidents, students=students)

# Log incident
@app.route('/log_incident', methods=['POST'])
def log_incident():
    student_id = request.form['student_id']
    fine_amount = request.form['fine_amount']
    meeting_schedule = request.form['meeting_schedule']
    exam_name = request.form['exam_name']
    exam_date = request.form['exam_date']
    invigilator_name = request.form['invigilator_name']
    squad_name = request.form['squad_name']
    exam_room = request.form['exam_room']
    mode_of_cheating = request.form['mode_of_cheating']

    # If "Others" is selected, use the value from the "other_mode" input
    if mode_of_cheating == "Others":
        mode_of_cheating = request.form['other_mode']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the student_id exists in the students table
        cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            flash('Invalid Student ID! Please provide a valid student ID.', 'error')
        else:
            # Insert the incident with the new fields
            cursor.execute('''INSERT INTO incidents 
                              (student_id, fine_amount, meeting_schedule, exam_name, exam_date, 
                               invigilator_name, squad_name, exam_room, mode_of_cheating) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (student_id, fine_amount, meeting_schedule, exam_name, exam_date,
                            invigilator_name, squad_name, exam_room, mode_of_cheating))
            conn.commit()
            flash('Incident logged successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'An error occurred: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)