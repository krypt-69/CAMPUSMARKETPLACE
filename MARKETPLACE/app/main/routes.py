from flask import Blueprint, render_template
from app.models import Product, Category

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Get fast-moving items (you'll add sample data later)
    fast_moving = Product.query.filter_by(is_fast_moving=True, is_sold=False).all()
    return render_template('main/index.html', fast_moving=fast_moving)

@main_bp.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('main/categories.html', categories=categories)