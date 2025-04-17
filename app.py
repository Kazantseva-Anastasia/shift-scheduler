from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import calendar
from config import Config

app = Flask(name)
app.config.from_object(Config)
db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    desired_days_off = db.Column(db.String(255), default='')
    desired_hours = db.Column(db.Integer, default=160)


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    hours = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref=db.backref('schedules', lazy=True))


# Helper Functions
def generate_schedule(employees, month, year, shift_type):
    # Clear old schedules for this month
    Schedule.query.filter(
        db.extract('month', Schedule.date) == month,
        db.extract('year', Schedule.date) == year
    ).delete()

    num_days = calendar.monthrange(year, month)[1]
    shift_hours = 12 if shift_type == '12h' else 9

    for employee in employees:
        days_off = list(map(int, employee.desired_days_off.split(','))) if employee.desired_days_off else []
        hours_assigned = 0

        for day in range(1, num_days + 1):
            current_date = datetime(year, month, day).date()

            if day in days_off or hours_assigned >= employee.desired_hours:
                # Day off
                schedule = Schedule(
                    user_id=employee.id,
                    date=current_date,
                    shift_type='off',
                    hours=0
                )
            else:
                # Work day
                schedule = Schedule(
                    user_id=employee.id,
                    date=current_date,
                    shift_type='day',
                    hours=shift_hours
                )
                hours_assigned += shift_hours

            db.session.add(schedule)

    db.session.commit()


# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.is_admin:
        return redirect(url_for('admin_dashboard'))

    today = datetime.now()
    schedules = Schedule.query.filter(
        db.extract('month', Schedule.date) == today.month,
        db.extract('year', Schedule.date) == today.year,
        Schedule.user_id == user.id
    ).order_by(Schedule.date).all()

    return render_template('employee.html', user=user, schedules=schedules)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or not User.query.get(session['user_id']).is_admin:
        return redirect(url_for('login'))

    employees = User.query.filter_by(is_admin=False).all()
    return render_template('admin.html', employees=employees)@app.route('/create_schedule', methods=['POST'])
def create_schedule():
    if 'user_id' not in session or not User.query.get(session['user_id']).is_admin:
        return redirect(url_for('login'))

    month = int(request.form['month'])
    year = int(request.form['year'])
    shift_type = request.form['shift_type']
    employees = User.query.filter_by(is_admin=False).all()

    generate_schedule(employees, month, year, shift_type)
    flash('Schedule created successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session or not User.query.get(session['user_id']).is_admin:
        return redirect(url_for('login'))

    employee = User.query.get_or_404(employee_id)

    if request.method == 'POST':
        employee.desired_days_off = request.form['days_off']
        employee.desired_hours = int(request.form['desired_hours'])
        db.session.commit()
        flash('Employee updated successfully')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_employee.html', employee=employee)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    if 'user_id' not in session or not User.query.get(session['user_id']).is_admin:
        return redirect(url_for('login'))

    username = request.form['username']
    password = generate_password_hash(request.form['password'])

    if User.query.filter_by(username=username).first():
        flash('Username already exists')
    else:
        employee = User(
            username=username,
            password=password,
            is_admin=False
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee added successfully')

    return redirect(url_for('admin_dashboard'))

if name == 'main':
    app.run(debug=True)