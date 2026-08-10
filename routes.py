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
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role

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
    
from sqlalchemy import cast, String
# admin dashboard route with search functionality
@routes.route('/admin', methods=['GET'])
@role_required("admin")
def admin_dashboard():

    query = request.args.get('query', '').strip()

    doctors = User.query.filter_by(role='doctor')
    patients = User.query.filter_by(role='patient')
    departments = Department.query
    appointments = Appointment.query

    if query:

        doctors = doctors.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%')) |
            (User.phone.ilike(f'%{query}%'))
        )

        patients = patients.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%')) |
            (User.phone.ilike(f'%{query}%'))
        )

        departments = departments.filter(
            (Department.name.ilike(f'%{query}%')) |
            (Department.description.ilike(f'%{query}%'))
        )

        appointments = appointments.filter(
            cast(Appointment.patient_id, String).ilike(f'%{query}%') |
            cast(Appointment.doctor_id, String).ilike(f'%{query}%') |
            cast(Appointment.appointment_date, String).ilike(f'%{query}%') |
            cast(Appointment.appointment_time, String).ilike(f'%{query}%')
        )

    appointments = appointments.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
        Appointment.id.desc()
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


from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
# route for adding doctor by admin
@routes.route('/admin_dashboard/add_doctor', methods=["GET", "POST"])
@role_required("admin")
def add_doctor():
    department = Department.query.all()

    if request.method == "POST":

        doctor_experience = request.form['exp'].strip()
        doctor_qualification = request.form['Qualification'].strip()
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        # fixed role
        department_id = request.form['department_id'].strip() or None
        phone = request.form['phone'].strip() or None

        # check if doctor already exists
        existing = User.query.filter_by(email=email).first()

        if existing:
            error = "Doctor with this email already exists."
            return render_template(
                "add_doctor.html",
                error_message=error,
                departments=department
            )

        # Hash password before storing it
        hashed_password = generate_password_hash(password)

        # add new doctor
        new_doctor = User(
            username=username,
            email=email,
            password=hashed_password,
            drexperience=doctor_experience,
            drqualification=doctor_qualification,
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

            current_app.logger.exception(
                "Error while adding doctor"
            )

            return render_template(
                "add_doctor.html",
                error_message="Something went wrong. Try again.",
                departments=department
            )

    return render_template(
        "add_doctor.html",
        departments=department
    )






# route for deleting doctor by admin
@routes.route('/admin_dashboard/delete_doctor/<int:doctor_id>', methods=['POST'])
@role_required("admin")
def delete_doctor(doctor_id):
    doctor = User.query.filter_by(id=doctor_id,role="doctor").first_or_404()
    try:
        db.session.delete(doctor)
        db.session.commit()
        flash('Doctor deleted successfully.', 'success')
    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Error deleting doctor"
        )

        flash(
            "Unable to delete doctor. Please try again.",
            "danger"
        )
    return redirect(url_for('routes.admin_dashboard'))




# route for deleting patient by admin
@routes.route('/admin_dashboard/delete_patient/<int:patient_id>', methods=['POST'])
@role_required("admin")
def delete_3264_patient(patient_id):
    patient = User.query.filter_by(id=patient_id,role="patient").first_or_404()
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
    patient = User.query.filter_by(id=patient_id,role="patient").first_or_404()
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
    doctor = User.query.filter_by(id=doctor_id,role="doctor").first_or_404()
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
    doctor = User.query.filter_by(id=doctor_id,role="doctor").first_or_404()
    departments = Department.query.all()
 
        # handling post method
    if request.method == 'POST':
        doctor.username = request.form['username'].strip()
        doctor.email = request.form['email'].strip()
        new_password = request.form.get('password', '').strip()

        if new_password:
            if len(new_password) < 8:
                flash("Password must contain at least 8 characters.", "danger")
                return redirect(
                    url_for('routes.edit_doctor', doctor_id=doctor_id)
                )

            doctor.password = generate_password_hash(new_password)
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
@routes.route(
    '/admin_dashboard/edit_patient/<int:patient_id>',
    methods=['GET', 'POST']
)
@role_required("admin")
def edit_3264_patient(patient_id):

    patient = User.query.filter_by(
        id=patient_id,
        role="patient"
    ).first_or_404()

    if request.method == 'POST':

        patient.username = request.form['username'].strip()
        patient.email = request.form['email'].strip()
        patient.phone = request.form['phone'].strip() or None

        # Update password only if admin entered a new password
        new_password = request.form.get('password', '').strip()

        if new_password:
            if len(new_password) < 8:
                flash(
                    "Password must contain at least 8 characters.",
                    "danger"
                )
                return redirect(
                    url_for(
                        'routes.edit_3264_patient',
                        patient_id=patient_id
                    )
                )

            patient.password = generate_password_hash(
                new_password
            )

        try:
            db.session.commit()

            flash(
                'Patient updated successfully.',
                'success'
            )

            return redirect(
                url_for('routes.admin_dashboard')
            )

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Error updating patient"
            )

            flash(
                'Unable to update patient. Please try again.',
                'danger'
            )

    return render_template(
        'edit_3264_patient.html',
        patient=patient
    )




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
@role_required("patient")
def patient_dashboard():

    doctors = User.query.filter_by(role='doctor')

    today = datetime.today().date()

    treatments = Treatment.query.join(Appointment).filter(
        Appointment.patient_id == session.get('user_id')
    ).all()

    appointments = Appointment.query.filter(
        Appointment.patient_id == session.get('user_id'),
        Appointment.appointment_date >= today,
        Appointment.status == 'scheduled'
    )

    departments = Department.query

    query = request.args.get('query', '').strip()

    if query:

        # Search doctors
        doctors = doctors.filter(
            (User.username.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%"))
        )

        # Search departments
        departments = departments.filter(
            (Department.name.ilike(f"%{query}%")) |
            (Department.description.ilike(f"%{query}%"))
        )

        # Search appointments using the doctor's name
        appointments = appointments.join(
            User,
            Appointment.doctor_id == User.id
        ).filter(
            User.username.ilike(f"%{query}%")
        )

    return render_template(
        'patient_dashboard.html',
        departments=departments,
        doctors=doctors,
        appointments=appointments,
        treatments=treatments,
        query=query
    )


# routes for viewing doctors by patient based on department on patient dashboard
@routes.route('/patient_dashboard/view_doctors_by_patient/<int:dept_id>/doctors')
@role_required("patient")
def view_doctors_by_patient(dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(department_id=dept_id, role='doctor').all()
    return render_template('view_doctors_by_patient.html', department=department, doctors=doctors)

# route for viewing doctor details by patient
@routes.route('/patient_dashboard/view_doctors_by_patient/doctor_detail_by_patient/<int:doctor_id>')
@role_required("patient")
def doctor_detail_by_patient(doctor_id):
    doctor = User.query.filter_by(id=doctor_id,role="doctor").first_or_404()
    return render_template('doctor_detail_by_patient.html', doctor=doctor)


# route for cancelling appointment by patient
@routes.route('/patient_dashboard/cancel_apt_by_pt/<int:appointment_id>', methods=["POST"])
@role_required("patient")
def cancel_apt_by_pt(appointment_id):
    patient_id = session["user_id"]

    appointment = Appointment.query.filter_by(
    id=appointment_id,
    patient_id=patient_id,
    status='scheduled').first_or_404()
    
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


    # Delete the appointment
    try:
        appointment.status = 'cancelled'

        if appointment.appointment_time == time(9, 0, 0):
            doctor_slot.morning = True
        else:
            doctor_slot.evening = True

        db.session.commit()

        flash(
            'Appointment cancelled successfully.',
            'success'
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Error cancelling patient appointment"
        )

        flash(
            'Unable to cancel appointment.',
            'danger'
        )

    return redirect(url_for('routes.patient_dashboard'))





from datetime import date
# route for checking doctor availability by patient
@routes.route('/view_doctor_by_patient/check_avail_by_patient/<int:doctor_id>', methods=['GET', 'POST'])
@role_required("patient")
def check_avail_by_patient(doctor_id):

    doctor = User.query.filter_by(id=doctor_id,role="doctor").first_or_404()

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


from sqlalchemy.exc import IntegrityError
# route for booking appointment by patient
@routes.route(
    '/check_avail_by_patient/booking_appointment/<int:doctor_id>',
    methods=['POST']
)
@role_required("patient")
def booking_appointment(doctor_id):

    patient_id = session.get('user_id')

    if not patient_id:
        return redirect(url_for('routes.login'))

    # Make sure the ID in the URL actually belongs to a doctor
    doctor = User.query.filter_by(
        id=doctor_id,
        role="doctor"
    ).first_or_404()

    # Get chosen slot from form
    selected = request.form.get("slot")

    if not selected:
        flash("Please select a slot.", "danger")
        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    # slot format = "YYYY-MM-DD|morning"
    # or "YYYY-MM-DD|evening"
    try:
        date_str, slot_type = selected.split("|", 1)

        appointment_date = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        flash("Invalid appointment slot.", "danger")
        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    # Validate slot type
    if slot_type not in ("morning", "evening"):
        flash("Invalid appointment slot.", "danger")
        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    # Set appointment time
    if slot_type == "morning":
        appointment_time = time(9, 0)
    else:
        appointment_time = time(17, 0)

    # Check if already booked
    existing = Appointment.query.filter_by(
    doctor_id=doctor_id,
    appointment_date=appointment_date,
    appointment_time=appointment_time,
    status='scheduled').first()

    if existing:
        flash("This slot is already booked.", "warning")
        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    # Find doctor's availability
    slot = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=appointment_date
    ).first()

    if not slot:
        flash("This appointment slot is not available.", "danger")
        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    # Make sure the selected slot is actually available
    if slot_type == "morning":

        if not slot.morning:
            flash("Morning slot is already booked.", "warning")
            return redirect(
                url_for(
                    'routes.check_avail_by_patient',
                    doctor_id=doctor_id
                )
            )

    else:

        if not slot.evening:
            flash("Evening slot is already booked.", "warning")
            return redirect(
                url_for(
                    'routes.check_avail_by_patient',
                    doctor_id=doctor_id
                )
            )

    # Create appointment
    new_appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        reason="General Checkup",
        status="scheduled"
    )

    try:

        # Mark slot as booked
        if slot_type == "morning":
            slot.morning = False
        else:
            slot.evening = False

        # Add appointment
        db.session.add(new_appt)

        # ONE commit for both operations
        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        flash(
            "This appointment slot was just booked by another patient.",
            "warning"
        )

        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Error while booking appointment"
        )

        flash(
            "Unable to book appointment. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                'routes.check_avail_by_patient',
                doctor_id=doctor_id
            )
        )

    flash("Appointment booked successfully!", "success")

    return redirect(
        url_for('routes.patient_dashboard')
    )


# route for editing patient profile by patient
@routes.route('/patient_dashboard/edit_profile_by_patient', methods=['GET', 'POST'])
@role_required("patient")
def edit_profile_by_patient():
    patient_id = session.get('user_id')
    patient = User.query.get_or_404(patient_id)

    if request.method == 'POST':

        patient.username = request.form['username'].strip()
        patient.email = request.form['email'].strip()
        patient.phone = request.form['phone'].strip() or None

        new_password = request.form.get('password', '').strip()

        if new_password:
            if len(new_password) < 8:
                flash(
                    "Password must contain at least 8 characters.",
                    "danger"
                )
                return redirect(
                    url_for("routes.edit_profile_by_patient")
                )

            patient.password = generate_password_hash(
                new_password
            )

        try:
            db.session.commit()

            flash(
                'Profile updated successfully.',
                'success'
            )

            return redirect(
                url_for('routes.patient_dashboard')
            )

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Error updating patient profile"
            )

            flash(
                'Unable to update profile.',
                'danger'
            )

    return render_template(
        'edit_profile_by_patient.html',
        patient=patient
    )

# route for viewing patient history by patient
@routes.route('/patient_dashboard/history_patient')
@role_required("patient")
def history_patient():
    patient_id = session.get('user_id')
    patient = User.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == session.get('user_id')).all()
    # treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('history_patient.html', patient=patient, appointments=appointments,treatments=treatments)





# # doctor dashboard route
@routes.route('/doctor_dashboard')
@role_required("doctor")
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
@role_required("doctor")
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



# route for adding treatment record by doctor
@routes.route(
    '/doctor_dashboard/add_treatment/<int:appointment_id>',
    methods=["GET", "POST"]
)
@role_required("doctor")
def add_treatment(appointment_id):

    doctor_id = session["user_id"]

    appointment = Appointment.query.filter_by(
        id=appointment_id,
        doctor_id=doctor_id,
        status="scheduled"
    ).first_or_404()

    patient_id = appointment.patient_id

    previous_visits = (
        Treatment.query
        .join(
            Appointment,
            Treatment.appointment_id == Appointment.id
        )
        .filter(Appointment.patient_id == patient_id)
        .filter(Appointment.doctor_id == doctor_id)
        .count()
    )

    next_visit_number = previous_visits + 1

    if request.method == "POST":

        treatment = Treatment(
            patient_id=appointment.patient_id,
            visit_date=datetime.utcnow(),
            visit_number=next_visit_number,
            visit_type=request.form.get("visit_type"),
            appointment_id=appointment.id,
            prescription=request.form.get("prescription"),
            diagnosis_text=request.form.get("diagnosis_text"),
            medicines=request.form.get("medicines")
        )

        try:

            db.session.add(treatment)

            # Complete appointment automatically
            appointment.status = "completed"

            # Make the slot available again
            doctor_slot = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id,
                date=appointment.appointment_date.date()
            ).first()

            if doctor_slot:

                if appointment.appointment_time == time(9, 0, 0):
                    doctor_slot.morning = True
                else:
                    doctor_slot.evening = True

            db.session.commit()

            flash(
                "Treatment added and appointment completed successfully.",
                "success"
            )

            return redirect(
                url_for("routes.doctor_dashboard")
            )

        except Exception as e:
            db.session.rollback()

            current_app.logger.exception(
                "Error adding treatment"
            )

            print("TREATMENT ERROR:", repr(e))

            flash(
                f"Unable to add treatment record: {e}",
                "danger"
            )

    return render_template(
        "add_treatment.html",
        appointment=appointment,
        visit_number=next_visit_number
    )


# route for cancelling appointment by doctor
@routes.route(
    '/doctor_dashboard/cancel_appointment/<int:appointment_id>',
    methods=['POST']
)
@role_required("doctor")
def cancel_apt_by_dr(appointment_id):

    doctor_id = session["user_id"]

    appointment = Appointment.query.filter_by(
    id=appointment_id,
    doctor_id=doctor_id,
    status='scheduled').first_or_404()

    slot = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=appointment.appointment_date.date()
    ).first()

    if not slot:
        flash(
            "Doctor availability record not found.",
            "danger"
        )
        return redirect(url_for('routes.doctor_dashboard'))

    try:
        # Mark appointment as cancelled
        appointment.status = 'cancelled'

        # Make the corresponding slot available again
        if appointment.appointment_time == time(9, 0, 0):
            slot.morning = True
        else:
            slot.evening = True

        # ONE commit for both changes
        db.session.commit()

        flash(
            'Appointment cancelled successfully.',
            'success'
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Error cancelling appointment by doctor"
        )

        flash(
            'Unable to cancel appointment. Please try again.',
            'danger'
        )

    return redirect(url_for('routes.doctor_dashboard'))
    
# route for viewing patient history by doctor
@routes.route('/doctor_dashboard/patient_history/<int:patient_id>')
@role_required("doctor")
def pt_history_by_doctor(patient_id):

    doctor_id = session["user_id"]

    patient = User.query.filter_by(
        id=patient_id,
        role="patient"
    ).first_or_404()

    treatments = (
        Treatment.query
        .join(Appointment, Treatment.appointment_id == Appointment.id)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor_id
        )
        .order_by(Treatment.visit_date.desc())
        .all()
    )

    return render_template(
        'pt_history_by_doctor.html',
        treatments=treatments,
        patient=patient
    )







    
# route for logout 
@routes.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('routes.login'))
