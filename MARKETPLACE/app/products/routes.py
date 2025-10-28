from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from app.models import Product, Category
from app import db

products_bp = Blueprint('products', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        condition = request.form.get('condition')
        contact_info = request.form.get('contact_info')
        category_id = request.form.get('category_id')
        is_fast_moving = bool(request.form.get('is_fast_moving'))
        
        # Handle image upload
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        
        # Create product
        new_product = Product(
            title=title,
            description=description,
            price=price,
            condition=condition,
            contact_info=contact_info,
            image=image_filename,
            category_id=category_id,
            is_fast_moving=is_fast_moving,
            seller_id=current_user.id
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Product listed successfully!', 'success')
        return redirect(url_for('products.my_products_list'))
    
    categories = Category.query.all()
    return render_template('products/create.html', categories=categories)

@products_bp.route('/my-products')
@login_required
def my_products_list():  # Changed from my_products to my_products_list
    # Get all products for the current user, ordered by newest first
    products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('products/my_products.html', products=products, categories=categories)

@products_bp.route('/all')
def all_products():
    # Get all products that are not sold, ordered by newest first
    products = Product.query.filter_by(is_sold=False).order_by(Product.created_at.desc()).all()
    return render_template('products/all.html', products=products)

@products_bp.route('/view/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if user paid to view contact details (you'll implement this later)
    has_paid = False
    
    return render_template('products/view.html', product=product, has_paid=has_paid)

# Add these additional routes for product management
@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if the current user owns this product
    if product.seller_id != current_user.id:
        flash('You can only edit your own products!', 'error')
        return redirect(url_for('products.my_products_list'))
    
    if request.method == 'POST':
        # Handle product editing
        product.title = request.form.get('title')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.condition = request.form.get('condition')
        product.category_id = request.form.get('category_id')
        product.is_fast_moving = bool(request.form.get('is_fast_moving'))
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Remove old image if exists
                if product.image:
                    old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                product.image = filename
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products.my_products_list'))
    
    categories = Category.query.all()
    return render_template('products/edit.html', product=product, categories=categories)

@products_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if the current user owns this product
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only delete your own products!'}), 403
    
    # Remove image file if exists
    if product.image:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Product deleted successfully!'})

@products_bp.route('/mark-sold/<int:product_id>', methods=['POST'])
@login_required
def mark_sold(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if the current user owns this product
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only mark your own products as sold!'}), 403
    
    product.is_sold = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Product marked as sold!'})