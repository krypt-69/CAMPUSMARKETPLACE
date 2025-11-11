# app/models.py
from flask_login import UserMixin
from flask import current_app
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
    
    # New contact fields
    phone_number = db.Column(db.String(20))
    campus_location = db.Column(db.String(100))
    hostel_name = db.Column(db.String(100))
    hostel_room = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20))
    
    # Seller preferences
    show_contact_details = db.Column(db.Boolean, default=True)
    contact_preference = db.Column(db.String(20), default='whatsapp')
    

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
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    condition = db.Column(db.String(20))
    contact_info = db.Column(db.Text)
    is_fast_moving = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_sold = db.Column(db.Boolean, default=False)
    Token = db.Column(db.Float, nullable=False)
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

    def is_unlocked_by(self, user):
        """Check if a user has unlocked this product"""
        if not user or not user.is_authenticated:
            return False
            
        unlock = ProductUnlock.query.filter_by(
            product_id=self.id,
            user_id=user.id,
            status='completed'
        ).first()
        
        return unlock is not None
    
    def get_unlock_fee(self):
        """Calculate unlock fee - you can customize this logic"""
        base_fee = current_app.config.get('UNLOCK_FEE', 1)  # Default KES 20
        # You could make expensive products cost more to unlock
        if self.price > 10000:
            return base_fee * 1
        return base_fee

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

class ProductUnlock(db.Model):
    __tablename__ = 'product_unlocks'
    
    id = db.Column(db.Integer, primary_key=True)
    # User who wants to unlock the product
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Product they want to unlock
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    # Seller of the product (for quick access)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)  # Unlock fee
    phone_number = db.Column(db.String(20))  # Payer's phone number
    checkout_request_id = db.Column(db.String(100), unique=True)
    merchant_request_id = db.Column(db.String(100))
    mpesa_receipt_number = db.Column(db.String(50))
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    unlocked_at = db.Column(db.DateTime)  # When they actually accessed the details
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('unlocked_products', lazy=True))
    product = db.relationship('Product', backref=db.backref('unlocks', lazy=True))
    seller = db.relationship('User', foreign_keys=[seller_id], backref=db.backref('buyer_unlocks', lazy=True))

    def __repr__(self):
        return f'<ProductUnlock {self.id} - User {self.user_id} -> Product {self.product_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    unlock_id = db.Column(db.Integer, db.ForeignKey('product_unlocks.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    product = db.relationship('Product', backref=db.backref('notifications', lazy=True))
    unlock = db.relationship('ProductUnlock', backref=db.backref('notification', lazy=True))

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'