from flask import Blueprint, render_template
from app.models import Product, Category

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Show all active, unsold products to everyone
    all_products = Product.query.filter_by(is_active=True, is_sold=False).limit(12).all()
    fast_moving = Product.query.filter_by(is_fast_moving=True, is_sold=False).all()
    return render_template('main/index.html', 
                         all_products=all_products, 
                         fast_moving=fast_moving)

@main_bp.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('main/categories.html', categories=categories)