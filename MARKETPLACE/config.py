import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///campus_marketplace.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'app/static/uploads/product_images'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # M-Pesa Configuration
    MPESA_CONSUMER_KEY = '4wG4bdDlPrrhXJD6LO2x7BnnAgJy5ITHgFdo3i9XDtorCFoq'
    MPESA_CONSUMER_SECRET = 'Z0B4Urr3fC6iZXBsNkQN6vIrmWDV6OfnvGJrS6V2xC2n9V3117PZZFn47XdYPWGK'
    MPESA_SHORTCODE = '174379'
    MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
    MPESA_BASE_URL = 'https://sandbox.safaricom.co.ke'
    BASE_URL = 'http://localhost:5000'
    LISTING_FEE = 1