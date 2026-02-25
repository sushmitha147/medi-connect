"""
MediConnect – Comprehensive Healthcare Management System
Flask application serving both the frontend and REST API.
"""

import os, json, random, datetime, uuid, smtplib, threading, time
from email.mime.text import MIMEText

# OTP in-memory store  {email: (otp, expires_timestamp)}
_otp_store = {}
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# ── App Setup ────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'mediconnect.db')
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'mediconnect-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

CORS(app)
db = SQLAlchemy(app)

# ── Database Models ──────────────────────────────────────────

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    city = db.Column(db.String(100))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    rating = db.Column(db.Float, default=4.0)
    phone = db.Column(db.String(20))
    available_from = db.Column(db.String(10), default='00:00')
    available_to = db.Column(db.String(10), default='23:59')
    has_ambulance = db.Column(db.Boolean, default=True)
    transport_eta = db.Column(db.Integer, default=15)  # minutes
    kmc_affiliated = db.Column(db.Boolean, default=False)
    video_consultation = db.Column(db.Boolean, default=True)
    beds_available = db.Column(db.Integer, default=50)
    icu_beds = db.Column(db.Integer, default=10)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    specialization = db.Column(db.String(100))
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    rating = db.Column(db.Float, default=4.5)
    experience = db.Column(db.Integer, default=10)
    fee = db.Column(db.Float, default=500)
    available_slots = db.Column(db.Text, default='09:00,10:00,11:00,14:00,15:00,16:00')
    photo_url = db.Column(db.String(300), default='/static/img/doctor-default.svg')
    languages = db.Column(db.String(200), default='English,Hindi')
    video_consult = db.Column(db.Boolean, default=True)
    hospital = db.relationship('Hospital', backref='doctors')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default='Demo User')
    email = db.Column(db.String(200), default='demo@mediconnect.in')
    phone = db.Column(db.String(20), default='+91 98765 43210')
    age = db.Column(db.Integer, default=28)
    gender = db.Column(db.String(20), default='Male')
    height = db.Column(db.Float, default=175)
    weight = db.Column(db.Float, default=72)
    blood_group = db.Column(db.String(10), default='O+')
    address = db.Column(db.String(300), default='123, MG Road, Bengaluru, Karnataka 560001')
    photo_url = db.Column(db.String(300), default='/static/img/user-default.svg')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), default=1)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    date = db.Column(db.String(20))
    time = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Confirmed')
    amount = db.Column(db.Float, default=500)
    payment_method = db.Column(db.String(30), default='UPI')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    doctor = db.relationship('Doctor', backref='appointments')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(200))
    in_stock = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300), default='/static/img/medicine-default.svg')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), default=1)
    items = db.Column(db.Text)  # JSON string
    total = db.Column(db.Float)
    status = db.Column(db.String(20), default='Processing')
    payment_method = db.Column(db.String(30), default='UPI')
    upi_transaction_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class BloodBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(10))
    units_available = db.Column(db.Integer)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    contact = db.Column(db.String(20))
    hospital = db.relationship('Hospital', backref='blood_bank')

class OrganDonor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    organ = db.Column(db.String(100))
    blood_group = db.Column(db.String(10))
    city = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Available')
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)
    registered_date = db.Column(db.String(20))
    hospital = db.relationship('Hospital', backref='organ_donors')

class CarePlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), default=1)
    title = db.Column(db.String(200))
    condition = db.Column(db.String(100))
    doctor = db.Column(db.String(200))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    progress = db.Column(db.Integer, default=0)  # 0-100
    tasks = db.Column(db.Text)  # JSON list of tasks
    medications = db.Column(db.Text)  # JSON list
    status = db.Column(db.String(20), default='Active')

class HealthRisk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), default=1)
    age = db.Column(db.Integer)
    bmi = db.Column(db.Float)
    smoker = db.Column(db.Boolean, default=False)
    diabetic = db.Column(db.Boolean, default=False)
    hypertensive = db.Column(db.Boolean, default=False)
    family_history = db.Column(db.Boolean, default=False)
    exercise_per_week = db.Column(db.Integer, default=0)
    risk_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class DietPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    condition = db.Column(db.String(100))   # e.g. 'diabetes', 'hypertension', 'general'
    bmi_range = db.Column(db.String(30))    # e.g. 'normal', 'overweight', 'obese'
    breakfast = db.Column(db.Text)
    lunch = db.Column(db.Text)
    dinner = db.Column(db.Text)
    snacks = db.Column(db.Text)
    water_litres = db.Column(db.Float, default=2.5)
    avoid_foods = db.Column(db.Text)
    lifestyle_tips = db.Column(db.Text)   # JSON list

class UPIPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), default=1)
    amount = db.Column(db.Float)
    upi_id = db.Column(db.String(100))
    purpose = db.Column(db.String(200))   # 'appointment', 'medicine', 'donation'
    status = db.Column(db.String(20), default='Pending')  # Pending, Success, Failed
    reference_id = db.Column(db.Integer)  # appointment_id or order_id
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


# ── Seed Data ────────────────────────────────────────────────

def seed_database():
    """Populate database with demo data for Indian hospitals, doctors, medicines."""
    if Hospital.query.first():
        return  # Already seeded

    hospitals_data = [
        {'name': 'AIIMS Delhi', 'address': 'Ansari Nagar, New Delhi', 'city': 'Delhi', 'lat': 28.5672, 'lng': 77.2100, 'rating': 4.8, 'phone': '011-26588500', 'transport_eta': 12, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 120, 'icu_beds': 30},
        {'name': 'Apollo Hospital', 'address': 'Jubilee Hills, Hyderabad', 'city': 'Hyderabad', 'lat': 17.4156, 'lng': 78.4075, 'rating': 4.6, 'phone': '040-23607777', 'transport_eta': 15, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 80, 'icu_beds': 20},
        {'name': 'Fortis Hospital', 'address': 'Bannerghatta Road, Bengaluru', 'city': 'Bengaluru', 'lat': 12.8891, 'lng': 77.5972, 'rating': 4.5, 'phone': '080-66214444', 'transport_eta': 18, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 60, 'icu_beds': 15},
        {'name': 'Manipal Hospital', 'address': 'HAL Airport Road, Bengaluru', 'city': 'Bengaluru', 'lat': 12.9592, 'lng': 77.6480, 'rating': 4.7, 'phone': '080-25024444', 'transport_eta': 10, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 90, 'icu_beds': 25},
        {'name': 'Medanta Hospital', 'address': 'Sector 38, Gurugram', 'city': 'Gurugram', 'lat': 28.4395, 'lng': 77.0266, 'rating': 4.6, 'phone': '0124-4141414', 'transport_eta': 20, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 70, 'icu_beds': 18},
        {'name': 'Narayana Health', 'address': 'Bommasandra, Bengaluru', 'city': 'Bengaluru', 'lat': 12.8165, 'lng': 77.6900, 'rating': 4.5, 'phone': '080-71222222', 'transport_eta': 22, 'kmc_affiliated': False, 'video_consultation': False, 'beds_available': 55, 'icu_beds': 12},
        {'name': 'Tata Memorial Hospital', 'address': 'Parel, Mumbai', 'city': 'Mumbai', 'lat': 18.9977, 'lng': 72.8418, 'rating': 4.8, 'phone': '022-24177000', 'transport_eta': 14, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 100, 'icu_beds': 28},
        {'name': 'CMC Vellore', 'address': 'Ida Scudder Road, Vellore', 'city': 'Vellore', 'lat': 12.9249, 'lng': 79.1353, 'rating': 4.9, 'phone': '0416-2281000', 'transport_eta': 16, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 110, 'icu_beds': 32},
        {'name': 'Kokilaben Hospital', 'address': 'Andheri West, Mumbai', 'city': 'Mumbai', 'lat': 19.1308, 'lng': 72.8268, 'rating': 4.5, 'phone': '022-30999999', 'transport_eta': 13, 'kmc_affiliated': False, 'video_consultation': True, 'beds_available': 75, 'icu_beds': 20},
        {'name': 'KMC Hospital Mangalore', 'address': 'Ambedkar Circle, Mangaluru', 'city': 'Mangaluru', 'lat': 12.8698, 'lng': 74.8425, 'rating': 4.7, 'phone': '0824-2445858', 'transport_eta': 10, 'kmc_affiliated': True, 'video_consultation': True, 'beds_available': 85, 'icu_beds': 22},
        {'name': 'KMC Hospital Manipal', 'address': 'Tiger Circle Road, Manipal', 'city': 'Manipal', 'lat': 13.3524, 'lng': 74.7927, 'rating': 4.8, 'phone': '0820-2922000', 'transport_eta': 8, 'kmc_affiliated': True, 'video_consultation': True, 'beds_available': 95, 'icu_beds': 28},
        {'name': 'Kasturba Medical College', 'address': 'Madhav Nagar, Manipal', 'city': 'Manipal', 'lat': 13.3498, 'lng': 74.7905, 'rating': 4.9, 'phone': '0820-2571201', 'transport_eta': 9, 'kmc_affiliated': True, 'video_consultation': True, 'beds_available': 150, 'icu_beds': 40},
    ]
    for h in hospitals_data:
        db.session.add(Hospital(**h))
    db.session.flush()

    specializations = ['Cardiologist', 'Neurologist', 'Orthopedic', 'Dermatologist', 'Pediatrician',
                       'General Physician', 'Ophthalmologist', 'ENT Specialist', 'Gastroenterologist',
                       'Pulmonologist', 'Psychiatrist', 'Urologist', 'Oncologist', 'Endocrinologist', 'Gynecologist']
    doctor_names = [
        'Dr. Rajesh Kumar', 'Dr. Priya Sharma', 'Dr. Arun Patel', 'Dr. Meena Reddy',
        'Dr. Sanjay Gupta', 'Dr. Anita Desai', 'Dr. Vikram Singh', 'Dr. Lakshmi Iyer',
        'Dr. Ramesh Nair', 'Dr. Sunita Joshi', 'Dr. Karthik Bhat', 'Dr. Deepa Menon',
        'Dr. Suresh Rao', 'Dr. Pooja Verma', 'Dr. Manoj Tiwari'
    ]
    lang_options = [
        'English,Hindi', 'English,Tamil', 'English,Telugu,Hindi',
        'English,Kannada', 'English,Malayalam', 'English,Marathi,Hindi',
        'English,Gujarati', 'English,Punjabi', 'English,Bengali',
        'English,Hindi,Kannada', 'English,Odia', 'English,Hindi,Tamil'
    ]
    for i, name in enumerate(doctor_names):
        db.session.add(Doctor(
            name=name,
            specialization=specializations[i],
            hospital_id=(i % 12) + 1,
            rating=round(random.uniform(4.0, 5.0), 1),
            experience=random.randint(5, 25),
            fee=random.choice([300, 500, 700, 1000, 1500]),
            available_slots='09:00,10:00,11:00,14:00,15:00,16:00',
            languages=random.choice(lang_options),
            video_consult=random.choice([True, True, True, False])
        ))

    medicines_data = [
        {'name': 'Paracetamol 500mg', 'category': 'Pain Relief', 'price': 25.0, 'description': 'For fever and mild pain relief', 'manufacturer': 'Cipla'},
        {'name': 'Amoxicillin 250mg', 'category': 'Antibiotic', 'price': 85.0, 'description': 'Broad-spectrum antibiotic', 'manufacturer': 'Sun Pharma'},
        {'name': 'Omeprazole 20mg', 'category': 'Antacid', 'price': 45.0, 'description': 'For acidity and GERD', 'manufacturer': "Dr. Reddy's"},
        {'name': 'Cetirizine 10mg', 'category': 'Antihistamine', 'price': 30.0, 'description': 'For allergies and cold symptoms', 'manufacturer': 'Cipla'},
        {'name': 'Metformin 500mg', 'category': 'Diabetes', 'price': 55.0, 'description': 'Blood sugar management', 'manufacturer': 'Lupin'},
        {'name': 'Atorvastatin 10mg', 'category': 'Cholesterol', 'price': 120.0, 'description': 'Cholesterol reduction', 'manufacturer': 'Ranbaxy'},
        {'name': 'Azithromycin 500mg', 'category': 'Antibiotic', 'price': 95.0, 'description': 'Macrolide antibiotic for infections', 'manufacturer': 'Zydus'},
        {'name': 'Ibuprofen 400mg', 'category': 'Pain Relief', 'price': 35.0, 'description': 'Anti-inflammatory pain reliever', 'manufacturer': 'Cipla'},
        {'name': 'Pantoprazole 40mg', 'category': 'Antacid', 'price': 65.0, 'description': 'Proton pump inhibitor for acid reflux', 'manufacturer': 'Sun Pharma'},
        {'name': 'Losartan 50mg', 'category': 'Blood Pressure', 'price': 80.0, 'description': 'For hypertension management', 'manufacturer': 'Torrent'},
        {'name': 'Aspirin 75mg', 'category': 'Blood Thinner', 'price': 20.0, 'description': 'Low-dose aspirin for heart health', 'manufacturer': 'Bayer'},
        {'name': 'Dolo 650mg', 'category': 'Pain Relief', 'price': 30.0, 'description': 'For fever and body pain', 'manufacturer': 'Micro Labs'},
        {'name': 'Vitamin D3 60000IU', 'category': 'Vitamin', 'price': 110.0, 'description': 'Weekly vitamin D supplement', 'manufacturer': 'USV'},
        {'name': 'B-Complex Forte', 'category': 'Vitamin', 'price': 45.0, 'description': 'Multi-vitamin B complex', 'manufacturer': 'Abbott'},
        {'name': 'Cough Syrup 100ml', 'category': 'Cough & Cold', 'price': 75.0, 'description': 'For dry and wet cough', 'manufacturer': 'Dabur'},
    ]
    for m in medicines_data:
        db.session.add(Medicine(**m))

    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    hospital_ids = list(range(1, 13))
    for bg in blood_groups:
        for h_id in random.sample(hospital_ids, k=random.randint(4, 8)):
            db.session.add(BloodBank(
                blood_group=bg,
                units_available=random.randint(3, 60),
                hospital_id=h_id,
                contact=f'+91 98765 {random.randint(10000, 99999)}'
            ))

    organs = ['Kidney', 'Liver', 'Heart', 'Lungs', 'Cornea', 'Bone Marrow', 'Pancreas', 'Skin']
    cities = ['Delhi', 'Mumbai', 'Bengaluru', 'Hyderabad', 'Chennai', 'Mangaluru', 'Manipal']
    donor_names = [
        'Rahul Sharma', 'Priya Menon', 'Arun Kumar', 'Sunita Reddy', 'Vikram Rao',
        'Anjali Patel', 'Mohan Singh', 'Deepa Iyer', 'Suresh Nair', 'Kavita Joshi',
        'Rajesh Bhat', 'Meena Desai', 'Kiran Verma', 'Pooja Tiwari', 'Amit Gupta'
    ]
    reg_dates = ['2025-06-15', '2025-08-22', '2025-10-01', '2024-12-11', '2026-01-05',
                 '2025-03-18', '2025-11-30', '2026-02-10', '2024-09-07', '2025-07-25',
                 '2026-01-20', '2025-05-14', '2024-11-02', '2025-12-28', '2026-02-01']
    for i in range(15):
        db.session.add(OrganDonor(
            name=donor_names[i],
            organ=random.choice(organs),
            blood_group=random.choice(blood_groups),
            city=random.choice(cities),
            contact=f'+91 98765 {random.randint(10000, 99999)}',
            status=random.choice(['Available', 'Available', 'Available', 'Matched', 'Pending']),
            hospital_id=random.randint(1, 12),
            registered_date=reg_dates[i]
        ))

    # Demo user
    db.session.add(User())
    # Demo appointments
    for i in range(3):
        db.session.add(Appointment(
            user_id=1, doctor_id=i+1,
            date=f'2026-03-{10+i}', time='10:00',
            status='Confirmed' if i == 0 else 'Completed', amount=500 + i*200
        ))

    # Demo care plans
    care_plans_data = [
        {
            'title': 'Diabetes Management Plan', 'condition': 'Type 2 Diabetes',
            'doctor': 'Dr. Sanjay Gupta', 'start_date': '2026-02-01', 'end_date': '2026-05-01',
            'progress': 60, 'status': 'Active',
            'tasks': json.dumps(['Monitor blood sugar daily', 'Walk 30 min/day', 'Follow low-glycemic diet', 'Monthly HbA1c test']),
            'medications': json.dumps(['Metformin 500mg – twice daily', 'Vitamin D3 – weekly'])
        },
        {
            'title': 'Hypertension Control Plan', 'condition': 'Hypertension',
            'doctor': 'Dr. Rajesh Kumar', 'start_date': '2026-01-15', 'end_date': '2026-04-15',
            'progress': 80, 'status': 'Active',
            'tasks': json.dumps(['Check BP every morning', 'Reduce salt intake', 'Meditation 15 min/day', 'Avoid caffeine']),
            'medications': json.dumps(['Losartan 50mg – once daily', 'Aspirin 75mg – with dinner'])
        },
    ]
    for cp in care_plans_data:
        db.session.add(CarePlan(**cp))

    # Diet plans
    diet_plans_data = [
        {
            'condition': 'general', 'bmi_range': 'normal',
            'breakfast': 'Oats porridge with banana, green tea',
            'lunch': 'Brown rice, dal, sabzi, salad, buttermilk',
            'dinner': 'Roti, paneer curry, soup',
            'snacks': 'Mixed nuts, fruits, sprouts',
            'water_litres': 2.5,
            'avoid_foods': 'Refined sugar, processed foods, excessive salt',
            'lifestyle_tips': json.dumps([
                'Exercise 30 minutes daily (walk, yoga, or gym)',
                'Sleep 7-8 hours per night',
                'Eat meals at fixed times',
                'Practice mindfulness or meditation for 10 min daily',
                'Limit screen time to 2 hours recreationally'
            ])
        },
        {
            'condition': 'diabetes', 'bmi_range': 'overweight',
            'breakfast': 'Methi paratha with curd, black coffee (no sugar)',
            'lunch': 'Brown rice / millets, dal, bitter gourd sabzi, salad',
            'dinner': 'Multigrain roti, palak paneer, soup',
            'snacks': 'Cucumber, sprouts, nuts (handful)',
            'water_litres': 3.0,
            'avoid_foods': 'White rice, maida, sugar, sweets, juices, alcohol',
            'lifestyle_tips': json.dumps([
                'Walk 45 minutes after meals to control blood sugar',
                'Monitor HbA1c every 3 months',
                'Avoid skipping meals – eat small portions frequently',
                'Reduce stress: yoga and meditation help control sugar',
                'Foot care is essential – check daily for cuts or sores'
            ])
        },
        {
            'condition': 'hypertension', 'bmi_range': 'overweight',
            'breakfast': 'Banana, oats, low-fat milk, herbal tea',
            'lunch': 'Rice, dal, vegetables, raita',
            'dinner': 'Roti, sabzi, lentil soup',
            'snacks': 'Fruits, low-sodium nuts',
            'water_litres': 2.5,
            'avoid_foods': 'Salt, pickles, papad, processed food, caffeine, alcohol',
            'lifestyle_tips': json.dumps([
                'Check blood pressure every morning',
                'Practice DASH diet (fruits, vegetables, low-fat dairy)',
                'Limit sodium intake to < 2g/day',
                'Do aerobic exercise 30 min/day, 5 days/week',
                'Manage weight – losing 5kg can drop BP by 5mmHg'
            ])
        },
        {
            'condition': 'cardiac', 'bmi_range': 'normal',
            'breakfast': 'Whole grain toast, egg whites, fresh juice (no sugar)',
            'lunch': 'Grilled fish or chicken, steamed vegetables, brown rice',
            'dinner': 'Soup, salad, dal, roti',
            'snacks': 'Walnuts, flaxseeds, fruits',
            'water_litres': 2.0,
            'avoid_foods': 'Red meat, fried foods, trans fats, ghee (excess), alcohol',
            'lifestyle_tips': json.dumps([
                'Take prescribed medications without fail',
                'Monitor heart rate daily',
                'No smoking – ever',
                'Do cardiac rehab exercises as advised by doctor',
                'Reduce stress using meditation, nature walks'
            ])
        }
    ]
    for dp in diet_plans_data:
        db.session.add(DietPlan(**dp))

    db.session.commit()
    print("[OK] Database seeded successfully!")


# ── Page Routes ──────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/emergency')
def emergency():
    return render_template('emergency.html')

@app.route('/symptoms')
def symptoms():
    return render_template('symptoms.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/appointments')
def appointments():
    return render_template('appointments.html')

@app.route('/medicines')
def medicines():
    return render_template('medicines.html')

@app.route('/telemedicine')
def telemedicine():
    return render_template('telemedicine.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/patient-portal')
def patient_portal():
    return render_template('patient_portal.html')

@app.route('/care-plans')
def care_plans():
    return render_template('care_plans.html')

@app.route('/organ-donors')
def organ_donors():
    return render_template('organ_donors.html')

@app.route('/diet-lifestyle')
def diet_lifestyle():
    return render_template('diet_lifestyle.html')

@app.route('/upi-payment')
def upi_payment():
    return render_template('upi_payment.html')


# ── API Routes ───────────────────────────────────────────────

@app.route('/api/hospitals')
def api_hospitals():
    hospitals = Hospital.query.all()
    return jsonify([{
        'id': h.id, 'name': h.name, 'address': h.address, 'city': h.city,
        'lat': h.lat, 'lng': h.lng, 'rating': h.rating, 'phone': h.phone,
        'available_from': h.available_from, 'available_to': h.available_to,
        'has_ambulance': h.has_ambulance, 'transport_eta': h.transport_eta,
        'kmc_affiliated': h.kmc_affiliated, 'video_consultation': h.video_consultation,
        'beds_available': h.beds_available, 'icu_beds': h.icu_beds
    } for h in hospitals])

@app.route('/api/doctors')
def api_doctors():
    doctors = Doctor.query.all()
    return jsonify([{
        'id': d.id, 'name': d.name, 'specialization': d.specialization,
        'hospital': d.hospital.name if d.hospital else '', 'rating': d.rating,
        'experience': d.experience, 'fee': d.fee,
        'available_slots': d.available_slots.split(',') if d.available_slots else [],
        'photo_url': d.photo_url,
        'languages': d.languages.split(',') if d.languages else ['English'],
        'video_consult': d.video_consult,
        'hospital_kmc': d.hospital.kmc_affiliated if d.hospital else False
    } for d in doctors])

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if request.method == 'POST':
        data = request.json
        appt = Appointment(
            doctor_id=data.get('doctor_id'),
            date=data.get('date'),
            time=data.get('time'),
            amount=data.get('amount', 500),
            payment_method=data.get('payment_method', 'UPI')
        )
        db.session.add(appt)
        db.session.commit()
        return jsonify({'success': True, 'id': appt.id, 'message': 'Appointment booked successfully!'})
    appts = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return jsonify([{
        'id': a.id, 'doctor': a.doctor.name if a.doctor else '',
        'specialization': a.doctor.specialization if a.doctor else '',
        'date': a.date, 'time': a.time, 'status': a.status,
        'amount': a.amount, 'payment_method': a.payment_method
    } for a in appts])

@app.route('/api/medicines')
def api_medicines():
    medicines = Medicine.query.all()
    return jsonify([{
        'id': m.id, 'name': m.name, 'category': m.category,
        'price': m.price, 'description': m.description,
        'manufacturer': m.manufacturer, 'in_stock': m.in_stock,
        'image_url': m.image_url
    } for m in medicines])

@app.route('/api/orders', methods=['POST'])
def api_orders():
    data = request.json or {}
    txn_id = None
    if data.get('payment_method', 'UPI') == 'UPI':
        txn_id = 'TXN' + uuid.uuid4().hex[:12].upper()
        upi_pay = UPIPayment(
            transaction_id=txn_id,
            amount=data.get('total', 0),
            upi_id=data.get('upi_id', 'mediconnect@upi'),
            purpose='medicine_order',
            status='Initiated',  # Real payment happens in UPI app
            completed_at=datetime.datetime.utcnow()
        )
        db.session.add(upi_pay)
    order = Order(
        items=json.dumps(data.get('items', [])),
        total=data.get('total', 0),
        payment_method=data.get('payment_method', 'UPI'),
        upi_transaction_id=txn_id
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({
        'success': True, 'id': order.id, 'transaction_id': txn_id,
        'customer_name': data.get('customer_name', ''),
        'delivery_address': data.get('delivery_address', ''),
        'message': f"Order placed for {data.get('customer_name', 'Customer')}! Delivering to: {data.get('delivery_address', 'address on file')}."
    })

@app.route('/api/profile')
def api_profile():
    user = User.query.first()
    if not user:
        return jsonify({})
    appts = Appointment.query.filter_by(user_id=user.id).all()
    orders = Order.query.filter_by(user_id=user.id).all()
    return jsonify({
        'name': user.name, 'email': user.email, 'phone': user.phone,
        'age': user.age, 'gender': user.gender, 'height': user.height,
        'weight': user.weight, 'blood_group': user.blood_group,
        'address': user.address, 'photo_url': user.photo_url,
        'appointments': [{
            'id': a.id, 'doctor': a.doctor.name if a.doctor else '',
            'date': a.date, 'status': a.status, 'amount': a.amount
        } for a in appts],
        'transactions': [{
            'id': o.id, 'total': o.total, 'status': o.status,
            'date': o.created_at.strftime('%Y-%m-%d') if o.created_at else ''
        } for o in orders]
    })

@app.route('/api/blood-bank')
def api_blood_bank():
    """Blood availability per blood group across multiple hospitals."""
    records = BloodBank.query.all()
    # Aggregate by blood group: count hospitals and total units
    agg = {}
    for b in records:
        bg = b.blood_group
        if bg not in agg:
            agg[bg] = {'blood_group': bg, 'total_units': 0, 'hospital_count': 0, 'hospitals': []}
        agg[bg]['total_units'] += b.units_available
        agg[bg]['hospital_count'] += 1
        agg[bg]['hospitals'].append({
            'hospital': b.hospital.name if b.hospital else 'Unknown',
            'units': b.units_available,
            'contact': b.contact
        })
    # Sort hospitals within each group by units desc
    for bg in agg:
        agg[bg]['hospitals'].sort(key=lambda x: x['units'], reverse=True)
    return jsonify(list(agg.values()))

@app.route('/api/organ-donors')
def api_organ_donors():
    """Organ donors with hospital and blood availability information."""
    donors = OrganDonor.query.all()
    result = []
    for d in donors:
        # Blood availability in this donor's registered hospital
        blood_avail = []
        if d.hospital_id:
            bb = BloodBank.query.filter_by(hospital_id=d.hospital_id).all()
            blood_avail = [{'blood_group': b.blood_group, 'units': b.units_available} for b in bb]
        result.append({
            'id': d.id, 'name': d.name, 'organ': d.organ, 'blood_group': d.blood_group,
            'city': d.city, 'contact': d.contact, 'status': d.status,
            'hospital': d.hospital.name if d.hospital else None,
            'hospital_kmc': d.hospital.kmc_affiliated if d.hospital else False,
            'hospital_video': d.hospital.video_consultation if d.hospital else False,
            'registered_date': d.registered_date,
            'blood_availability': blood_avail
        })
    return jsonify(result)

@app.route('/api/organ-donors/register', methods=['POST'])
def api_register_organ_donor():
    """Register as an organ donor."""
    data = request.json or {}
    donor = OrganDonor(
        name=data.get('name', 'Anonymous'),
        organ=data.get('organ', 'Kidney'),
        blood_group=data.get('blood_group', 'O+'),
        city=data.get('city', 'Unknown'),
        contact=data.get('contact', ''),
        status='Pending',
        hospital_id=data.get('hospital_id'),
        registered_date=datetime.datetime.utcnow().strftime('%Y-%m-%d')
    )
    db.session.add(donor)
    db.session.commit()
    return jsonify({'success': True, 'id': donor.id, 'message': 'Thank you for registering as an organ donor!'})

@app.route('/api/analyze-symptoms', methods=['POST'])
def api_analyze_symptoms():
    """Mock AI symptom analysis."""
    data = request.json or {}
    symptoms_text = data.get('symptoms', '')
    responses = {
        'headache': {'condition': 'Tension Headache / Migraine', 'severity': 'Mild to Moderate',
                     'advice': 'Rest, hydration, and over-the-counter pain relief. Consult a neurologist if persistent.',
                     'specialist': 'Neurologist'},
        'fever': {'condition': 'Viral Infection / Flu', 'severity': 'Moderate',
                  'advice': 'Stay hydrated, take paracetamol for fever. Consult if temperature exceeds 103°F.',
                  'specialist': 'General Physician'},
        'cough': {'condition': 'Upper Respiratory Tract Infection', 'severity': 'Mild',
                  'advice': 'Warm fluids, steam inhalation, cough syrup. See a pulmonologist if lasting > 2 weeks.',
                  'specialist': 'Pulmonologist'},
        'chest': {'condition': 'Possible Cardiac / Respiratory Issue', 'severity': 'High',
                  'advice': '⚠️ Seek immediate medical attention. Call 108 for emergency services.',
                  'specialist': 'Cardiologist'},
        'stomach': {'condition': 'Gastritis / Acid Reflux', 'severity': 'Mild to Moderate',
                    'advice': 'Avoid spicy food, take antacids. Consult gastroenterologist if persistent.',
                    'specialist': 'Gastroenterologist'},
    }
    result = {'condition': 'General Health Concern', 'severity': 'Mild',
              'advice': 'Based on your symptoms, we recommend consulting a General Physician for a proper diagnosis.',
              'specialist': 'General Physician'}
    for key, val in responses.items():
        if key in symptoms_text.lower():
            result = val
            break
    return jsonify({'success': True, 'analysis': result})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Expanded chatbot with rural health, PMJAY, ASHA, PHC knowledge."""
    data = request.json or {}
    message = data.get('message', '').lower()

    responses = [
        # Greetings
        (['hello', 'hi ', 'namaste', 'namaskar', 'vanakkam', 'sat sri akal'], "Namaste! 🙏 I'm MediConnect AI. I can help you with hospitals, medicines, ambulance booking, appointments, telemedicine, organ donation, PMJAY schemes, diet plans, and rural health services. Ask me anything!"),
        # Emergency
        (['emergency', 'urgent', '108', 'ambulance'], '🚨 For medical emergencies, call 108 immediately (free, 24/7). You can also book an ambulance from our Emergency page which shows your assigned driver name and live ETA.'),
        # Hospitals
        (['hospital', 'aspatal', 'doctor', 'dikhana', 'clinic'], 'Visit our Emergency page to see nearby hospitals on a live map with real-time bed availability, ICU count, ETA, and ambulance booking. We have 12+ partner hospitals including KMC-affiliated centres.'),
        # Appointments
        (['appointment', 'book doctor', 'consult', 'schedule'], 'Book appointments on our Appointments page. Choose from 15+ specialist doctors, select a time slot, and pay via UPI or card. Confirmation is instant!'),
        # Medicines / Rural access
        (['medicine', 'dawa', 'tablet', 'syrup', 'pharmacy', 'dawakhana'], 'Order medicines from our Medicines page. We offer doorstep delivery — ideal for rural areas far from pharmacies. Enter your name and delivery address at checkout, then pay via UPI.'),
        # Telemedicine
        (['telemedicine', 'video', 'online doctor', 'video call', 'remote'], '📹 Our Telemedicine feature connects you with specialist doctors via video call. Ideal for rural patients who cannot travel. Doctors speak Hindi, Tamil, Telugu, Kannada, Malayalam and more!'),
        # PMJAY / Ayushman Bharat
        (['pmjay', 'ayushman', 'pradhan mantri', 'free treatment', 'bpl', 'below poverty'], '🏥 PMJAY (Ayushman Bharat) provides free health coverage up to ₹5 lakh/year for BPL families. Most of our partner hospitals accept Ayushman Bharat cards. Show your e-card at the hospital.'),
        # ASHA Workers
        (['asha', 'asha worker', 'community health', 'gram', 'village'], '👩‍⚕️ ASHA workers are your first point of contact in villages. They can help with vaccinations, antenatal care, TB treatment, and refer you to PHCs (Primary Health Centres) or CHCs (Community Health Centres).'),
        # PHC / CHC
        (['phc', 'primary health', 'chc', 'community health centre', 'sub-centre'], '🏥 PHCs (Primary Health Centres) are government facilities for basic healthcare in rural areas. They provide free OPD, basic medicines, vaccinations, and maternal care. CHCs handle more complex cases.'),
        # Organ donors
        (['organ', 'donate organ', 'kidney', 'liver', 'cornea', 'bone marrow'], '❤️ Visit our Organ Donors page to register as a donor or find available donors. One donor can save up to 8 lives! Registration is free, voluntary, and can be revoked anytime.'),
        # Blood
        (['blood', 'blood group', 'transfusion', 'donate blood'], '🩸 Blood donation saves lives! Check blood availability on our Organ Donors page. You can also contact our partner hospitals directly for urgent blood requirements.'),
        # Diet & Nutrition
        (['diet', 'khana', 'food', 'nutrition', 'meal', 'eat'], '🥗 Visit our Diet & Lifestyle page for condition-specific meal plans — diabetes, hypertension, cardiac, obesity, and general wellness. Plans are based on Indian food preferences and seasonal items.'),
        # Diabetes
        (['diabetes', 'sugar', 'blood sugar', 'insulin', 'madhumeha'], '💊 For diabetes management: track blood sugar daily, follow a low-glycemic diet, walk 30 min/day, and take medicines as prescribed. Our Care Plans section has a dedicated Diabetes Management Plan.'),
        # Hypertension / BP
        (['bp', 'blood pressure', 'hypertension', 'high bp'], '❤️ Reduce BP naturally: reduce salt, exercise regularly, avoid stress, and monitor BP at home. Medications like Losartan, Amlodipine are available on our Medicines page.'),
        # Vaccination
        (['vaccine', 'vaccination', 'immunization', 'injection'], '💉 India\'s Universal Immunization Programme (UIP) offers free vaccines for children and adults at all PHCs and government hospitals. For COVID, flu, and travel vaccines, visit private clinics.'),
        # Mental Health
        (['mental', 'depression', 'anxiety', 'stress', 'mann', 'manasik'], '🧠 Mental health is as important as physical health. iCall (9152987821), Vandrevala Foundation (1860-2662-345) offer free counselling. Our Telemedicine also has Psychiatry consultations.'),
        # TB / Tuberculosis
        (['tb', 'tuberculosis', 'nikshay', 'cough blood'], '🫁 For TB treatment, visit any government PHC for free DOTS therapy under RNTCP. Nikshay Poshan Yojana offers ₹500/month nutritional support. Early diagnosis is key — persistent cough > 2 weeks needs testing.'),
        # Maternal / Pregnancy
        (['pregnant', 'pregnancy', 'antenatal', 'delivery', 'baby', 'maternity', 'prasav'], '🤱 Pregnant women should register with ASHA workers for free antenatal care. Janani Suraksha Yojana (JSY) provides cash benefits for institutional delivery. All government hospitals offer free delivery.'),
        # UPI / Payment
        (['upi', 'payment', 'pay', 'gpay', 'paytm', 'phonepe'], '💳 We support UPI for all payments. When you click "Pay via UPI", you will be redirected directly to your UPI app (GPay, PhonePe, Paytm) to complete the transaction securely.'),
        # Language
        (['language', 'hindi', 'tamil', 'telugu', 'kannada', 'translate', 'bhasha'], '🌐 MediConnect supports 12 Indian languages! Use the language dropdown in the left sidebar. The entire website and chatbot translate automatically — perfect for rural and non-English users.'),
        # KMC hospitals
        (['kmc', 'kasturba', 'manipal', 'mangalore hospital'], '🏥 KMC Hospital Mangalore, KMC Hospital Manipal, and Kasturba Medical College are KMC-affiliated hospitals in our network with the highest ratings (4.7–4.9★). They offer video consultation and ICU facilities.'),
        # Patient Portal
        (['patient portal', 'portal', 'dashboard', 'test result', 'report'], '📊 The Patient Portal shows your appointment history, test results, medication schedule, and 18+ personalized health tips. Access it from the left sidebar.'),
        # Care Plans
        (['care plan', 'treatment plan', 'health plan'], '📋 Care Plans are personalized health management programmes created by your doctor for chronic conditions like diabetes, hypertension, or cardiac issues. Track progress and tasks from your Patient Portal.'),
        # Rural health
        (['rural', 'village', 'gram panchayat', 'desh', 'gaon', 'remote area'], '🌾 MediConnect is built for rural India! Features include: telemedicine (no travel needed), doorstep medicine delivery, 12 language support, offline-friendly design, ASHA referral integration, and free 108 ambulance booking with live driver tracking.'),
        # Thanks
        (['thank', 'thanks', 'shukriya', 'dhanyavad', 'nandri'], "You're most welcome! 🙏 Stay healthy. If you or your family need medical help anytime, MediConnect is here 24/7. Call 108 for any emergency!"),
    ]

    reply = ("I'm your MediConnect AI health assistant! 🏥\n\n"
             "I can help with: hospitals, ambulance, appointments, medicines (doorstep delivery), telemedicine, "
             "organ donation, PMJAY/Ayushman Bharat, ASHA workers, PHC services, diet plans, diabetes, BP, "
             "TB, vaccination, mental health, and more.\n\n"
             "Ask me anything in any Indian language!")

    for (keywords, response) in responses:
        if any(kw in message for kw in keywords):
            reply = response
            break

    return jsonify({'reply': reply})

@app.route('/api/analytics')
def api_analytics():
    """Analytics data for dashboard."""
    return jsonify({
        'appointment_stats': {
            'labels': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
            'completed': [120, 145, 130, 168, 190, 210],
            'cancelled': [12, 9, 15, 8, 11, 7]
        },
        'disease_trends': {
            'labels': ['Diabetes', 'Hypertension', 'Respiratory', 'Cardiac', 'Orthopedic', 'Neurological'],
            'data': [28, 22, 18, 15, 10, 7]
        },
        'hospital_performance': {
            'labels': ['AIIMS', 'Apollo', 'Fortis', 'Manipal', 'Medanta'],
            'ratings': [4.8, 4.6, 4.5, 4.7, 4.6]
        },
        'kpis': {
            'total_patients': 12847,
            'success_rate': 97.3,
            'avg_wait_min': 18,
            'telemedicine_sessions': 3420
        }
    })

@app.route('/api/care-plans')
def api_care_plans():
    plans = CarePlan.query.all()
    return jsonify([{
        'id': p.id, 'title': p.title, 'condition': p.condition,
        'doctor': p.doctor, 'start_date': p.start_date, 'end_date': p.end_date,
        'progress': p.progress, 'status': p.status,
        'tasks': json.loads(p.tasks) if p.tasks else [],
        'medications': json.loads(p.medications) if p.medications else []
    } for p in plans])

@app.route('/api/health-risk', methods=['POST'])
def api_health_risk():
    """Calculate health risk score based on questionnaire inputs."""
    data = request.json or {}
    age = int(data.get('age', 30))
    bmi = float(data.get('bmi', 22))
    smoker = bool(data.get('smoker', False))
    diabetic = bool(data.get('diabetic', False))
    hypertensive = bool(data.get('hypertensive', False))
    family_history = bool(data.get('family_history', False))
    exercise = int(data.get('exercise_per_week', 3))

    # Rule-based risk score calculation
    score = 0
    if age > 60: score += 25
    elif age > 45: score += 15
    elif age > 35: score += 8
    if bmi > 30: score += 20
    elif bmi > 25: score += 10
    if smoker: score += 20
    if diabetic: score += 15
    if hypertensive: score += 15
    if family_history: score += 10
    if exercise == 0: score += 10
    elif exercise < 3: score += 5

    score = min(score, 100)
    if score >= 60: level = 'High'
    elif score >= 35: level = 'Moderate'
    else: level = 'Low'

    insights = []
    if smoker: insights.append('Quit smoking to reduce cardiovascular risk by 50% within 1 year.')
    if bmi > 25: insights.append('Achieving a healthy BMI reduces diabetes and heart disease risk significantly.')
    if exercise < 3: insights.append('30 minutes of moderate exercise 5 days/week can lower your risk score by 15 points.')
    if family_history: insights.append('With family history of disease, annual screening is strongly recommended.')
    if not insights: insights.append('You have a low risk profile! Maintain your healthy lifestyle.')

    # Suggest diet plan
    condition = 'diabetes' if diabetic else ('hypertension' if hypertensive else 'general')
    bmi_range = 'obese' if bmi > 30 else ('overweight' if bmi > 25 else 'normal')

    return jsonify({
        'success': True,
        'risk_score': score,
        'risk_level': level,
        'insights': insights,
        'recommendations': [
            'Schedule an annual health check-up at a MediConnect partner hospital.',
            'Track your vitals regularly using the Patient Portal.',
            'Follow your care plan if you have any chronic conditions.',
            f'Visit our Diet & Lifestyle page for a personalized {condition} diet plan.',
        ],
        'suggested_diet_condition': condition,
        'suggested_bmi_range': bmi_range
    })

@app.route('/api/diet-lifestyle', methods=['GET', 'POST'])
def api_diet_lifestyle():
    """Get diet and lifestyle recommendations."""
    if request.method == 'POST':
        data = request.json or {}
        condition = data.get('condition', 'general')
        bmi_range = data.get('bmi_range', 'normal')
    else:
        condition = request.args.get('condition', 'general')
        bmi_range = request.args.get('bmi_range', 'normal')

    # Try to find a matching plan
    plan = DietPlan.query.filter_by(condition=condition, bmi_range=bmi_range).first()
    if not plan:
        plan = DietPlan.query.filter_by(condition=condition).first()
    if not plan:
        plan = DietPlan.query.first()

    if not plan:
        return jsonify({'error': 'No diet plans found'}), 404

    return jsonify({
        'condition': plan.condition,
        'bmi_range': plan.bmi_range,
        'meals': {
            'breakfast': plan.breakfast,
            'lunch': plan.lunch,
            'dinner': plan.dinner,
            'snacks': plan.snacks
        },
        'water_litres': plan.water_litres,
        'avoid_foods': plan.avoid_foods,
        'lifestyle_tips': json.loads(plan.lifestyle_tips) if plan.lifestyle_tips else []
    })

@app.route('/api/diet-lifestyle/all')
def api_all_diet_plans():
    """Get all available diet condition options."""
    plans = DietPlan.query.all()
    return jsonify([{
        'id': p.id,
        'condition': p.condition,
        'bmi_range': p.bmi_range,
        'condition_label': p.condition.replace('_', ' ').title()
    } for p in plans])

@app.route('/api/upi-payment', methods=['POST'])
def api_upi_payment():
    """Process a UPI payment."""
    data = request.json or {}
    amount = float(data.get('amount', 0))
    upi_id = data.get('upi_id', '').strip()
    purpose = data.get('purpose', 'general')
    reference_id = data.get('reference_id')

    if not upi_id:
        return jsonify({'success': False, 'error': 'UPI ID is required'}), 400
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400

    # Validate UPI ID format (basic)
    if '@' not in upi_id:
        return jsonify({'success': False, 'error': 'Invalid UPI ID format. Use format: yourname@upihandle'}), 400

    # Simulate payment processing (95% success rate)
    success = random.random() < 0.95
    txn_id = 'TXN' + uuid.uuid4().hex[:12].upper()

    payment = UPIPayment(
        transaction_id=txn_id,
        amount=amount,
        upi_id=upi_id,
        purpose=purpose,
        status='Success' if success else 'Failed',
        reference_id=reference_id,
        completed_at=datetime.datetime.utcnow() if success else None
    )
    db.session.add(payment)
    db.session.commit()

    if success:
        return jsonify({
            'success': True,
            'transaction_id': txn_id,
            'amount': amount,
            'status': 'Success',
            'upi_id': upi_id,
            'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'Payment of ₹{amount:.2f} to MediConnect completed successfully!'
        })
    else:
        return jsonify({
            'success': False,
            'transaction_id': txn_id,
            'status': 'Failed',
            'message': 'Payment failed. Please check your UPI ID or try again.'
        }), 402

@app.route('/api/upi-payment/history')
def api_upi_history():
    """Get UPI payment history."""
    payments = UPIPayment.query.order_by(UPIPayment.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': p.id,
        'transaction_id': p.transaction_id,
        'amount': p.amount,
        'upi_id': p.upi_id,
        'purpose': p.purpose,
        'status': p.status,
        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '',
        'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M') if p.completed_at else None
    } for p in payments])

@app.route('/api/telemedicine-slots')
def api_telemedicine_slots():
    """Available telemedicine doctor slots."""
    doctors = Doctor.query.limit(8).all()
    return jsonify([{
        'id': d.id, 'name': d.name, 'specialization': d.specialization,
        'rating': d.rating, 'experience': d.experience,
        'fee': d.fee,
        'next_available': f'Today, {random.choice(["11:00 AM", "2:00 PM", "4:00 PM", "6:00 PM"])}',
        'languages': d.languages.split(',') if d.languages else ['English'],
        'video_consult': d.video_consult,
        'hospital': d.hospital.name if d.hospital else '',
        'hospital_kmc': d.hospital.kmc_affiliated if d.hospital else False
    } for d in doctors])

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handle file uploads for symptom checker."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    if f.filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
        f.save(filepath)
        return jsonify({'success': True, 'filename': f.filename})
    return jsonify({'error': 'Empty filename'}), 400


# ── OTP Sign-In ──────────────────────────────────────────────

def _send_otp_email(email, otp):
    """Send OTP via Gmail SMTP (runs in background thread)."""
    try:
        sender = os.environ.get('MAIL_USER', 'mediconnect.noreply@gmail.com')
        password = os.environ.get('MAIL_PASS', '')
        msg = MIMEText(
            f"""Your MediConnect Sign-In OTP is:\n\n  {otp}\n\nThis code expires in 5 minutes.
\nDo not share this code with anyone.
\nIf you did not request this, ignore this email.
\n— MediConnect Healthcare Team"""
        )
        msg['Subject'] = f'MediConnect Sign-In OTP: {otp}'
        msg['From'] = sender
        msg['To'] = email
        if password:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender, password)
                server.sendmail(sender, email, msg.as_string())
        else:
            # Fallback: print to console (dev mode)
            print(f'[MediConnect OTP] Email: {email}  OTP: {otp}')
    except Exception as e:
        print(f'[OTP Mail Error] {e}')

@app.route('/api/send-otp', methods=['POST'])
def api_send_otp():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400
    otp = str(random.randint(100000, 999999))
    _otp_store[email] = (otp, time.time() + 300)  # expires in 5 minutes
    threading.Thread(target=_send_otp_email, args=(email, otp), daemon=True).start()
    return jsonify({'success': True, 'message': f'OTP sent to {email}'})

@app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    code = data.get('otp', '').strip()
    entry = _otp_store.get(email)
    if not entry:
        return jsonify({'success': False, 'message': 'OTP not found. Please request a new one.'}), 400
    stored_otp, expires = entry
    if time.time() > expires:
        del _otp_store[email]
        return jsonify({'success': False, 'message': 'OTP has expired. Please request a new one.'}), 400
    if code != stored_otp:
        return jsonify({'success': False, 'message': 'Incorrect OTP. Please try again.'}), 400
    del _otp_store[email]  # Single use
    return jsonify({'success': True, 'message': f'Signed in as {email}', 'email': email})

# ── Main ─────────────────────────────────────────────────────

if __name__ == '__main__':
    db_is_new = not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) < 4096
    with app.app_context():
        if db_is_new:
            db.drop_all()
        db.create_all()
        seed_database()
    app.run(debug=True, port=5000)
