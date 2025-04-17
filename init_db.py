from app import app, db
from models import User

with app.app_context():
    db.create_all()

    # Create admin user if not exists
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()