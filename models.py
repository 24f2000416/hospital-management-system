from datetime import datetime, date, time
 
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy() 
 
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id'),
        nullable=True
    )

    username = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(500),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    blacklisted = db.Column(
        db.Boolean,
        default=False
    )

    drexperience = db.Column(
        db.Integer,
        nullable=True
    )

    drqualification = db.Column(
        db.String(150),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    department = db.relationship(
        'Department',
        back_populates='doctors'
    )

    reviews_received = db.relationship(
        'Review',
        back_populates='doctor'
    )

    availability_slots = db.relationship(
        'DoctorAvailability',
        back_populates='doctor'
    )

    patient_profile = db.relationship(
        'Patient',
        back_populates='user',
        uselist=False
    )

    appointments_as_patient = db.relationship(
        'Appointment',
        back_populates='patient',
        foreign_keys='Appointment.patient_id',
        cascade="all, delete",
        passive_deletes=True
    )

    doctor_appointments = db.relationship(
        'Appointment',
        back_populates='doctor',
        foreign_keys='Appointment.doctor_id'
    )


 
class Department(db.Model):
    __tablename__ = 'departments'
    blacklisted = db.Column(db.Boolean, default=False)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    

    doctors = db.relationship('User', back_populates='department')


class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blacklisted = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    user = db.relationship('User', back_populates='patient_profile')
    # appointments = db.relationship('Appointment', back_populates='patient')
    reviews_written = db.relationship('Review', back_populates='patient')


 
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    appointment_date = db.Column(db.DateTime, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)

    reason = db.Column(db.String(200), nullable=True)
    status = db.Column(
        db.String(50),
        nullable=False,
        default='scheduled'
    )

    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)

    # Prevent two appointments for the same doctor,
    # date and time
    __table_args__ = (
        db.UniqueConstraint(
            'doctor_id',
            'appointment_date',
            'appointment_time',
            name='uq_doctor_appointment_slot'
        ),
    )

    treatment_entry = db.relationship(
        'Treatment',
        back_populates='appointment',
        uselist=False
    )

    patient = db.relationship(
        'User',
        foreign_keys=[patient_id],
        back_populates='appointments_as_patient'
    )

    doctor = db.relationship(
        'User',
        foreign_keys=[doctor_id],
        back_populates='doctor_appointments'
    )

 
class Treatment(db.Model):
    __tablename__ = 'treatments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    visit_number = db.Column(db.Integer, nullable=False)
    visit_type = db.Column(db.String(100), nullable=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), unique=True, nullable=False)
    prescription= db.Column(db.Text, nullable=True)
    diagnosis_text = db.Column(db.Text, nullable=True)
    medicines = db.Column(db.Text, nullable=True)
    

    appointment = db.relationship('Appointment', back_populates='treatment_entry')

 
class DoctorAvailability(db.Model):
   

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    morning= db.Column(db.Boolean, default=False)
    evening= db.Column(db.Boolean, default=False)

    doctor = db.relationship('User', back_populates='availability_slots')

 
class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', back_populates='reviews_written')
    doctor = db.relationship('User', back_populates='reviews_received')
