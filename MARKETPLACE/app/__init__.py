# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    
    # Flask Configuration
    app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File Upload Configuration
    app.config['UPLOAD_FOLDER'] = 'app/static/uploads/product_images'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # M-Pesa Configuration - WITH CORRECT PASSKEY
    app.config['MPESA_CONSUMER_KEY'] = ''
    app.config['MPESA_CONSUMER_SECRET'] = ''
    app.config['MPESA_SHORTCODE'] = '174379'
    app.config['MPESA_PASSKEY'] = ''
    app.config['MPESA_BASE_URL'] = 'https://sandbox.safaricom.co.ke'
    app.config['BASE_URL'] = 'http://localhost:5000'
    app.config['LISTING_FEE'] = 1

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Import and register blueprints
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.products.routes import products_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    
    return app