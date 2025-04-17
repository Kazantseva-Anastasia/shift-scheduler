from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import calendar

app = Flask(name)
app.config['SECRET_KEY'] = 'ваш-секретный-ключ'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    days_off = db.Column(db.String(255), default='')
    desired_hours = db.Column(db.Integer, default=160)


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    hours = db.Column(db.Integer, nullable=False)


# Создаем администратора при первом запуске
@app.before_first_request
def create_admin():
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()


# Генерация графика
def generate_schedule(month, year, shift_hours):
    employees = User.query.filter_by(is_admin=False).all()
    days_in_month = calendar.monthrange(year, month)[1]

    # Удаляем старые записи
    Schedule.query.filter(
        db.extract('month', Schedule.date) == month,
        db.extract('year', Schedule.date) == year
    ).delete()

    for employee in employees:
        requested_days_off = list(map(int, employee.days_off.split(','))) if employee.days_off else []
        hours_assigned = 0

        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day).date()

            if day in requested_days_off or hours_assigned >= employee.desired_hours:
                # Выходной
                shift = Schedule(
                    user_id=employee.id,
                    date=date,
                    shift_type='выходной',
                    hours=0
                )
            else:
                # Рабочий день
                shift = Schedule(
                    user_id=employee.id,
                    date=date,
                    shift_type='дневная' if shift_hours == 8 else 'ночная',
                    hours=shift_hours
                )
                hours_assigned += shift_hours

            db.session.add(shift)

    db.session.commit()


# Маршруты
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.is_admin:
        return redirect(url_for('admin'))

    current_month = datetime.now().month
    schedules = Schedule.query.filter(
        Schedule.user_id == user.id,
        db.extract('month', Schedule.date) == current_month
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
            flash('Неверное имя пользователя или пароль')

    return render_template('login.html')


# ... (остальные маршруты аналогично предыдущей версии)

if name == 'main':
    db.create_all()
    app.run(debug=True)