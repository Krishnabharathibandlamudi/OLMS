from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename

# Initialize Flask App
app = Flask(__name__)

# --- Configuration ---
# CRITICAL FIX: Session and flash require a secret key
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(24))

# Database Configuration (Use environment variables in production!)
# NOTE: Using 'monkey' and 'tail' credentials as defined in database.sql
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'Sathvik@sql')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'college')

# Email Configuration (Use App Passwords for security)
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', "sathvikguntupalli2005@gmail.com")
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', "cdvq qpwa bbyc zirz")
MENTOR_EMAIL = os.environ.get('MENTOR_EMAIL', "mentor@college.edu") 
DEFAULT_MENTOR_ID = os.environ.get('DEFAULT_MENTOR_ID', "F2001") 

# File Upload Configuration (Simulated path, not persistent in this environment)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

mysql = MySQL(app)

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    # Robustly check if a filename is provided and if its extension is allowed
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(recipient, subject, body, attachment=None, filename='attachment.pdf'):
    """Sends an email with optional attachment."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        if attachment:
            # Note: attachment.read() consumes the file stream. The route must handle this.
            # We rewind the stream if it was read previously (e.g., during filename check)
            try:
                attachment.seek(0)
            except:
                pass 
                
            part = MIMEApplication(attachment.read(), Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        print(f"Email successfully sent to {recipient}")
    except Exception as e:
        print(f"Email sending failed to {recipient}:", e)
        flash(f"Email notification failed. Server log: {e}", 'error') 


@app.route('/', methods=['GET'])
def home():
    """Checks session and renders the main page with user dashboard data if logged in."""
    student_data = None
    faculty_data = None
    applications = None
    previous_leaves = None
    certificates = None
    cert_applications = None
    student_history_data = None
    history_heading = None
    
    # 1. Check if user is logged in
    if 'role' in session:
        cursor = mysql.connection.cursor()
        id_num = session['id_num']
        
        try:
            if session['role'] == 'student':
                # Fetch student details: (id_num, name)
                cursor.execute("SELECT id_num, name FROM student_details WHERE id_num=%s", (id_num,))
                student_raw = cursor.fetchone()
                
                check_flag = session.get('check_history', '')
                
                if student_raw:
                    # Structure: [(id_num, check_flag)] where id_num is index 0 and check_flag is index 1
                    student_data = [(student_raw[0], check_flag)] 
                
                # Fetch previous leaves (for student dashboard view)
                cursor.execute("SELECT id, student_email, start_date, end_date, reason, status FROM leave_application WHERE student_email=%s ORDER BY created_at DESC", (id_num,))
                previous_leaves = cursor.fetchall()

                # Fetch certificate applications (for student dashboard view)
                # Columns: id (0), student_email (1), event_name (2), certificate_path (3), status (4)
                cursor.execute("SELECT id, student_email, event_name, certificate_path, status FROM certificate_application WHERE student_email=%s ORDER BY created_at DESC", (id_num,))
                certificates = cursor.fetchall()


            elif session['role'] == 'faculty':
                # Fetch faculty details
                cursor.execute("SELECT id_num, name, is_hod FROM faculty WHERE id_num=%s", (id_num,))
                faculty_raw = cursor.fetchone()

                if faculty_raw:
                    is_hod = faculty_raw[2] # Assuming is_hod is the 3rd column (index 2)
                    # Structure expected by index.html: (faculty.0.5) is_hod flag
                    faculty_data = [(faculty_raw[0], faculty_raw[1], None, None, None, is_hod)]
                
                # Fetch pending leave applications for faculty dashboard
                # Status 'c' is 'Waiting for faculty' and 'b' is 'Waiting for HoD'
                applications_query = "SELECT id, student_email, start_date, end_date, reason FROM leave_application WHERE status IN ('c', 'b') ORDER BY created_at ASC"
                cursor.execute(applications_query)
                applications = cursor.fetchall()
                
                # Fetch pending certificate applications for faculty dashboard (status 'c')
                # Columns: id (0), student_email (1), event_name (2), certificate_path (3)
                cert_query = "SELECT id, student_email, event_name, certificate_path FROM certificate_application WHERE status='c' ORDER BY created_at ASC"
                cursor.execute(cert_query)
                cert_applications = cursor.fetchall()

        except Exception as e:
            flash(f"Error loading dashboard data: {e}", 'error')
            return redirect(url_for('logout'))
        finally:
            cursor.close()

    # Clear the history flag after fetching to hide the temporary history table on refresh
    session.pop('check_history', None)

    # Pass all relevant data to the index template
    return render_template('index.html', 
                           student=student_data, 
                           faculty=faculty_data,
                           applications=applications,
                           previous=previous_leaves,
                           certificates=certificates, 
                           cert_applications=cert_applications,
                           student_data=student_history_data,
                           heading=history_heading)


@app.route('/register', methods=['POST'])
def register():
    """Allows a new student to register an account, handling data from the modal."""
    
    id_num = request.form.get('id_num')
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash("Passwords do not match.", 'error')
        return redirect(url_for('home', error='umatched_password1')) 

    if len(id_num) > 20:
        flash("Student ID cannot be longer than 12 characters.", 'error')
        return redirect(url_for('home', error='long_id'))

    cursor = mysql.connection.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT * FROM student_details WHERE id_num=%s", (id_num,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        flash("This ID is already registered. Please log in.", 'error')
        cursor.close()
        return redirect(url_for('home', error='incorrect_login_password'))
    
    try:
        # Insert new student, assigning the DEFAULT_MENTOR_ID
        cursor.execute("INSERT INTO student_details (id_num, name, email, phone, password, mentor_id) VALUES (%s, %s, %s, %s, %s, %s)",
                       (id_num, name, email, phone, password, DEFAULT_MENTOR_ID))
        mysql.connection.commit()
        
        flash("Registration successful! You can now log in.", 'success')
        return redirect(url_for('home'))

    except Exception as e:
        flash(f"Database error during registration: {e}", 'error')
        mysql.connection.rollback()
        return redirect(url_for('home'))
    finally:
        cursor.close()


@app.route('/login', methods=['POST'])
def login():
    """Handles user login via the modal in navigation_bar.html."""
    id_num = request.form.get('id_num')
    password = request.form.get('password')

    if not id_num or not password:
        flash("Please enter ID and password.", 'warning')
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor()

    # Check student
    cursor.execute("SELECT * FROM student_details WHERE id_num=%s AND password=%s", (id_num, password))
    student = cursor.fetchone()
    if student:
        session['id_num'] = id_num
        session['role'] = 'student'
        cursor.close()
        flash("Student logged in successfully.", 'success')
        return redirect(url_for('home'))

    # Check faculty
    cursor.execute("SELECT * FROM faculty WHERE id_num=%s AND password=%s", (id_num, password))
    faculty = cursor.fetchone()
    cursor.close()
    if faculty:
        session['id_num'] = id_num
        session['role'] = 'faculty'
        flash("Faculty logged in successfully.", 'success')
        return redirect(url_for('home'))

    flash("Invalid credentials. Please try again.", 'error')
    return redirect(url_for('home', error='incorrect_login_password'))


@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    """Handles a student submitting a new leave application."""
    if 'role' not in session or session['role'] != 'student':
        flash("Unauthorized access.", 'error')
        return redirect(url_for('home'))

    student_id = session['id_num'] # Use ID from session
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    reason = request.form.get('reason')

    if not from_date or not to_date:
        flash("Please select both From date and To date.", 'warning')
        return redirect(url_for('home'))

    try:
        cursor = mysql.connection.cursor()
        # Insert into leave_application. Status 'c' means 'Waiting for faculty'
        cursor.execute("INSERT INTO leave_application (student_email, reason, start_date, end_date, status) VALUES (%s, %s, %s, %s, %s)",
                       (student_id, reason, from_date, to_date, "c")) 
        mysql.connection.commit()
        cursor.close()

        # Notify mentor (using the global MENTOR_EMAIL)
        send_email(MENTOR_EMAIL, "New Leave Application",
                   f"Student {student_id} applied for leave from {from_date} to {to_date}.\nReason: {reason}")

        flash("Leave application submitted successfully. Mentor notified.", 'success')
    except Exception as e:
        flash(f"Database error during leave application: {e}", 'error')
        mysql.connection.rollback()

    return redirect(url_for('home'))


@app.route('/apply_certificate', methods=['POST'])
def apply_certificate():
    """Handles a student submitting a new Industrial Certification application with a file upload."""
    if 'role' not in session or session['role'] != 'student':
        flash("Unauthorized access.", 'error')
        return redirect(url_for('home'))

    student_id = session['id_num']
    event_name = request.form.get('event_name')
    certificate_file = request.files.get('certificate_file')
    
    if not event_name:
        flash("Please enter the name of the certification event.", 'warning')
        return redirect(url_for('home'))

    file_path = "N/A - File Not Uploaded"
    filename = None
    
    # --- File Upload Validation and Handling ---
    if certificate_file and certificate_file.filename != '':
        if allowed_file(certificate_file.filename):
            filename = secure_filename(certificate_file.filename)
            # Simulate saving the file and storing its path
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            flash("Invalid file type. Only PDF, PNG, JPG, JPEG allowed.", 'warning')
            return redirect(url_for('home'))
    else:
        # File is mandatory for certification
        flash("Please upload the certification document.", 'warning')
        return redirect(url_for('home'))
    # -------------------------------------------

    try:
        cursor = mysql.connection.cursor()
        # Insert into certificate_application. Status 'c' means 'Pending'
        cursor.execute("INSERT INTO certificate_application (student_email, event_name, certificate_path, status) VALUES (%s, %s, %s, %s)",
                       (student_id, event_name, file_path, "c")) 
        mysql.connection.commit()
        
        # Notify mentor (Pass the file object to send_email before cursor close)
        # Note: certificate_file stream is still open here
        send_email(MENTOR_EMAIL, "New Industrial Certification Request",
                   f"Student {student_id} submitted a certificate for review.\nEvent: {event_name}\nFile Path (Simulated): {file_path}",
                   attachment=certificate_file, filename=filename)

        flash("Industrial Certification application submitted successfully. Mentor notified.", 'success')
    except Exception as e:
        flash(f"Database error during certificate application: {e}", 'error')
        mysql.connection.rollback()
    finally:
        cursor.close()
        # In a real scenario, you'd ensure the file stream is closed here if it hadn't been by send_email

    return redirect(url_for('home'))


@app.route('/history', methods=['POST'])
def history():
    """Handles student checking their own leave history (sets flag)."""
    if session.get('role') != 'student':
        flash("History access restricted.", 'error')
        return redirect(url_for('home'))

    # Set a flag in the session to trigger the display of the history table in home()
    session['check_history'] = 'checked' 
    return redirect(url_for('home'))
        

@app.route('/delete', methods=['POST'])
def delete():
    """Allows student to delete a pending leave application."""
    if 'role' not in session or session['role'] != 'student':
        flash("Unauthorized access.", 'error')
        return redirect(url_for('home'))
        
    leave_id = request.form.get('num')
    student_id = session['id_num']

    if not leave_id:
        flash("Invalid request to delete leave.", 'error')
        return redirect(url_for('home'))
        
    try:
        cursor = mysql.connection.cursor()
        # Only allow deletion if status is 'c' (waiting for faculty/pending)
        cursor.execute("DELETE FROM leave_application WHERE id=%s AND student_email=%s AND status='c'", (leave_id, student_id))
        
        if cursor.rowcount > 0:
            mysql.connection.commit()
            flash(f"Leave application (ID: {leave_id}) deleted successfully.", 'success')
        else:
            flash("Leave application not found or cannot be deleted (already approved/denied/forwarded).", 'warning')
        cursor.close()
    except Exception as e:
        flash(f"Database error during deletion: {e}", 'error')
        mysql.connection.rollback()
        
    # Re-render the history view after deletion
    session['check_history'] = 'checked'
    return redirect(url_for('home'))


@app.route('/update_leave', methods=['POST'])
def update_leave():
    """Handles faculty approving/denying a leave application based on their role (HoD or Faculty)."""
    if 'role' not in session or session['role'] != 'faculty':
        flash("Unauthorized access.", 'error')
        return redirect(url_for('home'))

    leave_id = request.form.get('id_num')
    action = request.form.get('action') # 'approve' or 'deny'
    comment = request.form.get('comment') 

    if not leave_id or action not in ['approve', 'deny']:
        flash("Invalid request.", 'error')
        return redirect(url_for('home'))

    # Status codes: 'a' (Granted), 'b' (Waiting for HoD), 'c' (Waiting for faculty), 'r' (Denied)
    
    cursor = mysql.connection.cursor()
    
    # 1. Determine new status based on current faculty role
    try:
        cursor.execute("SELECT is_hod FROM faculty WHERE id_num=%s", (session['id_num'],))
        is_hod = cursor.fetchone()[0]
    except:
        is_hod = 'n'
    
    new_status = 'r' # Default to denied
    if action == 'approve':
        if is_hod == 'y':
            # HoD approves -> Final approval
            new_status = 'a' 
        else:
            # Faculty approves -> Next step is HoD
            new_status = 'b' 
    
    try:
        # 2. Update status
        cursor.execute("UPDATE leave_application SET status=%s WHERE id=%s", (new_status, leave_id))
        mysql.connection.commit()

        # 3. Fetch student email for notification
        cursor.execute("SELECT student_email FROM leave_application WHERE id=%s", (leave_id,))
        student_email = cursor.fetchone()[0]
        
        # 4. Notify student
        status_text = {
            'a': 'granted by the HoD.',
            'b': 'approved by your faculty and is now waiting for HoD approval.',
            'r': 'denied.',
        }.get(new_status, 'updated.')
        
        send_email(student_email, "Leave Application Update",
                   f"Your leave application (ID: {leave_id}) has been {status_text}.\nMentor comment: {comment or 'N/A'}")

        flash(f"Leave application (ID: {leave_id}) updated to {status_text}.", 'success')
    except Exception as e:
        flash(f"Error updating leave application: {e}", 'error')
        mysql.connection.rollback()
    finally:
        cursor.close()

    return redirect(url_for('home'))


@app.route('/update_certificate', methods=['POST'])
def update_certificate():
    """Handles faculty approving/denying a certificate application."""
    if 'role' not in session or session['role'] != 'faculty':
        flash("Unauthorized access.", 'error')
        return redirect(url_for('home'))

    cert_id = request.form.get('cert_id')
    action = request.form.get('action') # 'approve' or 'deny'

    if not cert_id or action not in ['approve', 'deny']:
        flash("Invalid request.", 'error')
        return redirect(url_for('home'))

    new_status = 'a' if action == 'approve' else 'r' # a: Approved, r: Denied

    try:
        cursor = mysql.connection.cursor()
        # 1. Update status
        cursor.execute("UPDATE certificate_application SET status=%s WHERE id=%s", (new_status, cert_id))
        mysql.connection.commit()

        # 2. Fetch student email for notification
        cursor.execute("SELECT student_email FROM certificate_application WHERE id=%s", (cert_id,))
        student_email = cursor.fetchone()[0]
        
        # 3. Notify student
        status_text = "approved" if new_status == 'a' else "denied"
        
        send_email(student_email, "Industrial Certification Update",
                   f"Your Industrial Certification application (ID: {cert_id}) has been {status_text} by the faculty.")

        flash(f"Certification application (ID: {cert_id}) has been {status_text}.", 'success')
    except Exception as e:
        flash(f"Error updating certificate application: {e}", 'error')
        mysql.connection.rollback()
    finally:
        cursor.close()

    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    """Logs the user out."""
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('home'))


if __name__ == '__main__':
    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
