from models import db, User, Department, Appointment, Treatment, DoctorAvailability



from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import time, date
from models import db, User, Department, Appointment
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, redirect, url_for
from datetime import datetime, timedelta
# Create a Blueprint instance
routes = Blueprint('routes', __name__)


# route for home page
@routes.route('/')
def index():
    return render_template('base.html')

from werkzeug.security import generate_password_hash, check_password_hash


# route for registration
from flask_login import login_user

@routes.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()

        # Required fields
        if not username or not email or not password:
            flash(
                "Username, email and password are required.",
                "danger"
            )
            return redirect(url_for('routes.register'))

        # Password validation
        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for('routes.register'))

        # Phone validation
        if len(phone) != 10 or not phone.isdigit():
            flash(
                "Phone number must contain exactly 10 digits.",
                "danger"
            )
            return redirect(url_for('routes.register'))

        # Check whether username or email already exists
        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:
            flash(
                "Username or email already exists.",
                "danger"
            )
            return redirect(url_for('routes.register'))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create new patient
        user = User(
            username=username,
            email=email,
            password=hashed_password,
            role='patient',
            phone=phone
        )

        db.session.add(user)
        db.session.commit()

        # Automatically log in the newly registered patient
        login_user(user)

        flash(
            "Registration successful!",
            "success"
        )

        # Change this to your patient's dashboard route
        return redirect(url_for('routes.patient_dashboard'))

    departments = Department.query.all()

    return render_template(
        'register.html',
        departments=departments
    )


# route for login
from werkzeug.security import check_password_hash

@routes.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            if user.blacklisted:
                return render_template(
                    'login.html',
                    mess="You are blacklisted. Contact admin."
                )

            session.clear()

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect(
                    url_for('routes.admin_dashboard')
                )

            elif user.role == 'doctor':
                session['department_id'] = user.department_id

                return redirect(
                    url_for('routes.doctor_dashboard')
                )

            elif user.role == 'patient':
                return redirect(
                    url_for('routes.patient_dashboard')
                )

            else:
                session.clear()

                return render_template(
                    'login.html',
                    mess="Invalid user role."
                )

        return render_template(
            'login.html',
            mess="Invalid credentials"
        )

    return render_template('login.html')


#  Authorization part
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first.", "danger")
            return redirect(url_for("routes.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("routes.login"))

            if session.get("role") not in roles:
                flash("Unauthorized access.", "danger")
                return redirect(url_for("routes.index"))

            return f(*args, **kwargs)
        return decorated
    return decorator
    
# admin dashboard route with search functionality
@routes.route('/admin', methods=['GET'])
@role_required("admin")
def admin_dashboard():
    query = request.args.get('query', '').strip()

    # impoartant models for passing to admin dashboard
    doctors = User.query.filter_by(role='doctor')
    patients = User.query.filter_by(role='patient')
    departments = Department.query
    appointments = Appointment.query

    # If a search query exists, filter results
    if query:
        
        
        # Search in doctors
        doctors = doctors.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%')) |
            (User.phone.ilike(f'%{query}%'))
        )


        # Search in patients
        patients = patients.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%')) |
            (User.phone.ilike(f'%{query}%'))
        )

        # Search in departments
        departments = departments.filter(
            Department.name.ilike(f'%{query}%') |
            Department.description.ilike(f'%{query}%')
        )

        # Search in appointments
        appointments = appointments.filter(
            (Appointment.patient_id.ilike(f'%{query}%')) |
            (Appointment.doctor_id.ilike(f'%{query}%')) |
            (Appointment.appointment_date.ilike(f'%{query}%')) |
            (Appointment.appointment_time.ilike(f'%{query}%'))
        )

    return render_template(
        'admin_dashboard.html',
        doctors=doctors.all(),
        patients=patients.all(),
        departments=departments.all(),
        appointments=appointments.all(),
        query=query
    )




#  route for viewing patient history by admin
@routes.route('/admin_dashboard/patient_history_by_admin/<int:patient_id>',methods=['GET'])
@role_required("admin")
def patient_history_by_admin(patient_id):
    patient = User.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('pt_history_by_admin.html', patient=patient, appointments=appointments,treatments=treatments)


# route for adding department by admin
@routes.route('/admin_dashboard/add_department', methods=["GET", "POST"])
@role_required("admin")
def add_department():
    if request.method == "POST":
        department_name = request.form['name'].strip()
        description = request.form['description'].strip()
        
        # check if department already exists
        existing = Department.query.filter_by(name=department_name).first()
        if existing:
            error = "Department already exists."
            return render_template("add_department.html", error_message=error)

        # add new department
        new_department = Department( name=department_name, description=description)
        try:
            db.session.add(new_department)
            db.session.commit()
            return redirect(url_for("routes.admin_dashboard"))
        except Exception as e:
            db.session.rollback()
            return render_template("add_department.html", error_message="Something went wrong. Try again.")

    return render_template("add_department.html")



# route for adding doctor by admin
@routes.route('/admin_dashboard/add_doctor', methods=["GET", "POST"])
@role_required("admin")
def add_doctor():
    department = Department.query.all()
    if request.method == "POST":
        
        doctor_experience = request.form['exp'].strip()
        doctor_qualification = request.form['Qualification'].strip()
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
          # fixed role
        department_id = request.form['department_id'].strip() or None
        phone = request.form['phone'].strip() or None

        # check if doctor already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            error = "Doctor with this ID already exists."
            return render_template("add_doctor.html", error_message=error)

        # add new doctor
        new_doctor = User(
            
            username=username,
            email=email,
            password=password,
            drexperience = doctor_experience,
            drqualification = doctor_qualification,
            role='doctor',
            department_id=department_id,
            phone=phone
        )

        try:
            db.session.add(new_doctor)
            db.session.commit()
            return redirect(url_for("routes.admin_dashboard"))
        except Exception as e:
            db.session.rollback()
            return render_template("add_doctor.html", error_message="Something went wrong. Try again.")

    return render_template("add_doctor.html",departments=department)




# route for deleting doctor by admin
@routes.route('/admin_dashboard/delete_doctor/<int:doctor_id>', methods=['POST'])
@role_required("admin")
def delete_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    try:
        db.session.delete(doctor)
        db.session.commit()
        flash('Doctor deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting doctor: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))




# route for deleting patient by admin
@routes.route('/admin_dashboard/delete_patient/<int:patient_id>', methods=['POST'])
@role_required("admin")
def delete_3264_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('Patient deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting Patient: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))




# route for blacklisting patient by admin
@routes.route('/admin_dashboard/blacklist_patient/<int:patient_id>', methods=['POST'])
@role_required("admin")
def blacklist_3264_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    try:
        patient.blacklisted = True
        db.session.commit()
        flash('patient blacklisted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error blacklisting patient: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))

@routes.route('/admin_dashboard/blacklist_doctor/<int:doctor_id>', methods=['POST'])
@role_required("admin")
def blacklist_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    try:
        doctor.blacklisted = True
        db.session.commit()
        flash('Doctor blacklisted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error blacklisting doctor: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))


# route for editing doctor by admin
@routes.route('/admin_dashboard/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@role_required("admin")
def edit_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    departments = Department.query.all()
 
        # handling post method
    if request.method == 'POST':
        doctor.username = request.form['username'].strip()
        doctor.email = request.form['email'].strip()
        doctor.password = request.form['password'].strip()
        doctor.drexperience = request.form['exp'].strip()
        doctor.drqualification = request.form['Qualification'].strip()
        doctor.department_id = request.form['department_id'].strip() or None
        doctor.phone = request.form['phone'].strip() or None

        try:
            db.session.commit()
            flash('Doctor updated successfully.', 'success')
            return redirect(url_for('routes.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating doctor: {e}', 'danger')

    return render_template('edit_doctor.html', doctor=doctor, departments=departments)



# route for editing patient by admin
@routes.route('/admin_dashboard/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@role_required("admin")
def edit_3264_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    
    # handling post methodhandling post method
    if request.method == 'POST':
        patient.username = request.form['username'].strip()
        patient.email = request.form['email'].strip()
        patient.password = request.form['password'].strip()
        patient.phone = request.form['phone'].strip() or None

        try:
            db.session.commit()
            flash('patient updated successfully.', 'success')
            return redirect(url_for('routes.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating patient: {e}', 'danger')

    return render_template('edit_3264_patient.html', patient=patient)




# routes for viewing doctors by admin based on department on admin dashboard
@routes.route('/admin_dashboard/view_doctors_by_department/<int:dept_id>/doctors')
@role_required("admin")
def view_doctors_by_admin(dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(department_id=dept_id, role='doctor').all()
    return render_template('view_doctors_by_admin.html', department=department, doctors=doctors)


# routes for deleting department by admin
@routes.route('/admin_dashboard/delete_department/<int:dept_id>', methods=['POST'])
@role_required("admin")
def delete_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    try:
        db.session.delete(department)
        db.session.commit()
        flash('Department deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting department: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))


# departmetn blacklist route
@routes.route('/admin_dashboard/blacklist_department/<int:dept_id>', methods=['POST'])
@role_required("admin")
def blacklist_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    try:
        department.blacklisted = True
        db.session.commit()
        flash('Department blacklisted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error blacklisting department: {e}', 'danger')
    return redirect(url_for('routes.admin_dashboard'))




from datetime import time, date


# patient dashboard route
@routes.route('/patient_dashboard')
def patient_dashboard():
    doctors = User.query.filter_by(role='doctor')
    today = datetime.today().date() 
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == session.get('user_id')).all()
    appointments = Appointment.query.filter(Appointment.patient_id == session.get('user_id'),Appointment.appointment_date >= today,Appointment.status == 'scheduled')
    departments=Department.query
    
    
    
    
    query = request.args.get('query', '').strip()
    
        # If a search query exists, filter results
    if query:
        
        
        # Search in doctors
        
        doctors = doctors.filter(
        (User.username.ilike(f"%{query}%")) |
        (User.email.ilike(f"%{query}%")) |
        (User.phone.ilike(f"%{query}%"))
    )

        
        

        # Search in departments
        departments = departments.filter(
            Department.name.ilike(f'%{query}%') |
            Department.description.ilike(f'%{query}%')
        )

        # Search in appointments
        appointments = appointments.filter(
            (Appointment.patient_id.ilike(f'%{query}%')) |
            (Appointment.doctor_id.ilike(f'%{query}%')) |
            (Appointment.appointment_date.ilike(f'%{query}%')) |
            (Appointment.appointment_time.ilike(f'%{query}%'))
        )
    
    
    return render_template('patient_dashboard.html',departments=departments,doctors=doctors,appointments=appointments,treatments=treatments,query=query)


# routes for viewing doctors by patient based on department on patient dashboard
@routes.route('/patient_dashboard/view_doctors_by_patient/<int:dept_id>/doctors')
def view_doctors_by_patient(dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(department_id=dept_id, role='doctor').all()
    return render_template('view_doctors_by_patient.html', department=department, doctors=doctors)

# route for viewing doctor details by patient
@routes.route('/patient_dashboard/view_doctors_by_patient/doctor_detail_by_patient/<int:doctor_id>')
def doctor_detail_by_patient(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    return render_template('doctor_detail_by_patient.html', doctor=doctor)


# route for cancelling appointment by patient
@routes.route('/patient_dashboard/cancel_apt_by_pt/<int:appointment_id>', methods=["POST"])
def cancel_apt_by_pt(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != session.get('user_id'):
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('routes.patient_dashboard'))
    
    # Extract date only if DoctorAvailability.date is Date type
    apt_date = appointment.appointment_date.date()  # datetime.date object

    doctor_slot = DoctorAvailability.query.filter_by(
        doctor_id=appointment.doctor_id,
        date=apt_date
    ).first()

    if not doctor_slot:
        # Create a new slot record if none exists
        doctor_slot = DoctorAvailability(
            doctor_id=appointment.doctor_id,
            date=apt_date,
            morning=False,
            evening=False
        )
        db.session.add(doctor_slot)

    # Mark the correct slot as available
    if appointment.appointment_time == time(9, 0, 0):
        doctor_slot.morning = True
    else:
        doctor_slot.evening = True

    db.session.commit()

    # Delete the appointment
    try:
        appointment.status = 'cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling appointment: {e}', 'danger')

    return redirect(url_for('routes.patient_dashboard'))





from datetime import date
# route for checking doctor availability by patient
@routes.route('/view_doctor_by_patient/check_avail_by_patient/<int:doctor_id>', methods=['GET', 'POST'])
def check_avail_by_patient(doctor_id):

    doctor = User.query.get_or_404(doctor_id)

    today = date.today()

    upcoming_week = []

    for i in range(7):

        current_day = today + timedelta(days=i)

        upcoming_week.append(current_day)

        row = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            date=current_day
        ).first()

        if row is None:

            row = DoctorAvailability(
                doctor_id=doctor_id,
                date=current_day,
                morning=True,
                evening=True
            )

            db.session.add(row)

    db.session.commit()

    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date.in_(upcoming_week)
    ).order_by(
        DoctorAvailability.date
    ).all()

    return render_template(
        "check_avail_by_patient.html",
        doctor=doctor,
        availabilities=availabilities
    )

# route for booking appointment by patient
@routes.route('/check_avail_by_patient/booking_appointment/<int:doctor_id>', methods=['POST'])
def booking_appointment(doctor_id):
    print("booking appointment called")
  
    patient_id = session.get('user_id')
    if not patient_id:
        return redirect(url_for('routes.login'))

    # Get chosen slot from form
    selected = request.form.get("slot")
    if not selected:
        flash("Please select a slot.", "danger")
        return redirect(url_for('routes.check_avail_by_patient', doctor_id=doctor_id))

    # slot format = "YYYY-MM-DD|morning" or "YYYY-MM-DD|evening"
    date_str, slot_type = selected.split("|")
    appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Set appointment time
    if slot_type == "morning":
        appointment_time = datetime.strptime("09:00", "%H:%M").time()
    else:
        appointment_time = datetime.strptime("17:00", "%H:%M").time()

    # Check if already booked
    existing = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    ).first()

    if existing:
        flash("You have already booked this slot.", "warning")
        return redirect(url_for('routes.check_avail_by_patient', doctor_id=doctor_id))

    # Create NEW appointment
    new_appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        reason="General Checkup",
        status="scheduled"
    )
    print(new_appt)
    db.session.add(new_appt)
    db.session.commit()

    # Mark slot as booked
    slot = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=appointment_date
    ).first()

    if slot_type == "morning":
        slot.morning = False
    else:
        slot.evening = False

    db.session.commit()

    flash("Appointment booked successfully!", "success")
    return redirect(url_for('routes.patient_dashboard'))


# route for editing patient profile by patient
@routes.route('/patient_dashboard/edit_profile_by_patient', methods=['GET', 'POST'])
def edit_profile_by_patient():
    patient_id = session.get('user_id')
    patient = User.query.get_or_404(patient_id)

    if request.method == 'POST':
        patient.username = request.form['username'].strip()
        patient.email = request.form['email'].strip()
        patient.password = request.form['password'].strip()
        patient.phone = request.form['phone'].strip() or None

        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('routes.patient_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {e}', 'danger')
    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    appointments = Appointment.query.all()
    departments=Department.query.all()
    return render_template('edit_profile_by_patient.html',departments=departments,doctors=doctors,patients=patients,appointments=appointments,patient=patient)


# route for viewing patient history by patient
@routes.route('/patient_dashboard/history_patient')
def history_patient():
    patient_id = session.get('user_id')
    patient = User.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == session.get('user_id')).all()
    # treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('history_patient.html', patient=patient, appointments=appointments,treatments=treatments)





# # doctor dashboard route
@routes.route('/doctor_dashboard')
def doctor_dashboard():
    assigned_patients = (
    Appointment.query
    .filter(
        Appointment.doctor_id == session.get('user_id'),
        Appointment.status == 'completed'
    ).distinct()
    .all()
)

    today = datetime.today().date() 
    appointments_future = Appointment.query.filter(Appointment.doctor_id == session.get('user_id'),Appointment.appointment_date >= today,Appointment.status=='scheduled').all()
    return render_template('doctor_dashboard.html',appointments_future=appointments_future,assigned_patients=assigned_patients)




@routes.route('/doctor/availability', methods=['GET', 'POST'])
def doctor_availability():
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect(url_for('routes.login'))

    today = datetime.now().date()

    upcoming_week = []
    for offset in range(7):
        this_day = today + timedelta(days=offset)
        upcoming_week.append(this_day)

        already_saved = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            date=this_day
        ).first()

        if not already_saved:
            new_day = DoctorAvailability(
                doctor_id=doctor_id,
                date=this_day,
                morning=True,
                evening=True
            )
            db.session.add(new_day)

    db.session.commit()

# post logic block changes to booked slots
    if request.method == 'POST':

        for this_day in upcoming_week:

            text_date = this_day.isoformat()

            morning_key = f"morning_{text_date}"
            evening_key = f"evening_{text_date}"

            is_morning = morning_key in request.form
            is_evening = evening_key in request.form

            row = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id,
                date=this_day
            ).first()

            if not row:
                continue

            from sqlalchemy import func
            from datetime import time

            # Check if morning slot is booked
            morning_booked = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                func.date(Appointment.appointment_date) == this_day,
                Appointment.appointment_time >= time(9,0),
                Appointment.appointment_time < time(12,0),
                Appointment.status.in_(["scheduled", "completed"])
            ).first()

            # Check if evening slot is booked
            evening_booked = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                func.date(Appointment.appointment_date) == this_day,
                Appointment.appointment_time >= time(17,0),
                Appointment.appointment_time < time(21,0),
                Appointment.status.in_(["scheduled", "completed"])
            ).first()

            # Block morning change
            if morning_booked and (row.morning != is_morning):
                flash(f"Morning slot on {this_day} is already booked. You cannot change it.", "danger")
            else:
                row.morning = is_morning

            # Block evening change
            if evening_booked and (row.evening != is_evening):
                flash(f"Evening slot on {this_day} is already booked. You cannot change it.", "danger")
            else:
                row.evening = is_evening

        db.session.commit()
        return redirect(url_for('routes.doctor_availability'))


    week_rows = DoctorAvailability.query.filter(DoctorAvailability.doctor_id == doctor_id,DoctorAvailability.date.in_(upcoming_week)).order_by(DoctorAvailability.date).all()

    return render_template(
        '3264doctor_availability.html',
        days_availability=week_rows
    )



# route for marking appointment as complete by doctor
@routes.route('/patient_dashboard/mark_as_complete_by_dr/<int:appointment_id>')
def mark_as_complete_by_dr(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    slot = DoctorAvailability.query.filter_by(
        doctor_id=appointment.doctor_id,
        date=appointment.appointment_date.date()
    ).first()
    
    if appointment.appointment_time == time(9, 0, 0):
        slot.morning = True
    else:
        slot.evening = True
    db.session.commit()
    
    
    try:
        db.session.commit()
        flash('Appointment completed', 'success')
        return redirect(url_for('routes.doctor_dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error int marking complete: {e}', 'danger')

    return redirect(url_for('routes.doctor_dashboard'))


# route for adding treatment record by doctor
@routes.route('/doctor_dashboard/add_treatment/<int:appointment_id>', methods=["GET", "POST"])
def add_treatment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient_id = appointment.patient_id
    doctor_id = appointment.doctor_id

    # Count previous treatments for this patient by this doctor
    previous_visits = (
        Treatment.query
        .join(Appointment, Treatment.appointment_id == Appointment.id)
        .filter(Appointment.patient_id == patient_id)
        .filter(Appointment.doctor_id == doctor_id)
        .count()
    )
    next_visit_number = previous_visits + 1
    
    if request.method == "POST":
        treatment = Treatment(
            patient_id=appointment.patient_id,             # Auto from appointment
            visit_date=datetime.utcnow(),                  # Auto
            visit_number = next_visit_number,
            visit_type=request.form.get("visit_type"),
            appointment_id=appointment.id,                 # Same appointment
            prescription=request.form.get("prescription"),
            diagnosis_text=request.form.get("diagnosis_text"),
            medicines=request.form.get("medicines")
        )

        db.session.add(treatment)
        db.session.commit()

        flash("Treatment record added successfully!", "success")
        return redirect(url_for("routes.doctor_dashboard"))

    return render_template("add_treatment.html", appointment=appointment,visit_number=next_visit_number)


# route for cancelling appointment by doctor
@routes.route('/patient_dashboard/cancel_treatment/<int:appointment_id>')
def cancel_apt_by_dr(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    slot = DoctorAvailability.query.filter_by(
        doctor_id=appointment.doctor_id,
        date=appointment.appointment_date.date()
    ).first()
    if appointment.appointment_time == time(9, 0, 0):
        slot.morning = True
    else:
        slot.evening = True
    db.session.commit()
    try:
        appointment.status = 'cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling appointment: {e}', 'danger')
    return redirect(url_for('routes.doctor_dashboard'))
    
# route for viewing patient history by doctor
@routes.route('/doctor_dashboard/view_patient_history/<int:patient_id>')
def pt_history_by_doctor(patient_id):   
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id , Appointment.doctor_id == session.get('user_id'),Appointment.status == 'completed').all()
    return render_template('pt_history_by_doctor.html', treatments=treatments)







    
# route for logout 
@routes.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('routes.login'))
