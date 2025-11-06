# app/models.py
from flask_login import UserMixin
from app import db, login_manager
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', backref='seller', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Changed from 'name' to 'title'
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))  # Changed from 'image_url' to 'image'
    condition = db.Column(db.String(20))  # Added condition field
    contact_info = db.Column(db.Text)  # Added contact_info field
    is_fast_moving = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)  # Added for payment control
    is_sold = db.Column(db.Boolean, default=False)
    
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    payments = db.relationship(
        'Payment',
        backref='product',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Product {self.title}>'

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    checkout_request_id = db.Column(db.String(100), unique=True)
    merchant_request_id = db.Column(db.String(100))
    mpesa_receipt_number = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    transaction_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Payment {self.id} - {self.status}>'