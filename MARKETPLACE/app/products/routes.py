from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from app.models import Product, Category
from app import db
from app.mpesa import MpesaGateway  # We'll create this

products_bp = Blueprint('products', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        # Check if this is a payment confirmation
        payment_method = request.form.get('payment_method')
        
        if payment_method == 'mpesa':
            # Handle M-Pesa payment first
            return handle_mpesa_payment(request)
        elif payment_method == 'free':
            # Free listing during beta
            return handle_free_listing(request)
        else:
            # Regular form submission - show payment step
            categories = Category.query.all()
            return render_template('products/create.html', categories=categories)
    
    categories = Category.query.all()
    return render_template('products/create.html', categories=categories)

def handle_mpesa_payment(request):
    """Handle M-Pesa payment for product listing"""
    try:
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        condition = request.form.get('condition')
        category_id = request.form.get('category_id')
        is_fast_moving = bool(request.form.get('is_fast_moving'))
        phone_number = request.form.get('mpesa_phone')
        
        # Validate phone number
        if not phone_number:
            flash('Please provide your M-Pesa phone number', 'error')
            return redirect(url_for('products.create_product'))
        
        # Format phone number (remove + and spaces, ensure it starts with 254)
        phone_number = phone_number.replace('+', '').replace(' ', '')
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number
        
        # Get delivery information
        delivery_option = request.form.get('delivery_option')
        contact_info = ""
        
        if delivery_option == 'free':
            contact_info = request.form.get('delivery_address', '')
        elif delivery_option == 'paid':
            delivery_fee = request.form.get('delivery_fee', '0')
            contact_info = f"Paid delivery: KES {delivery_fee}"
        else:  # meetup
            contact_info = "Campus meetup - contact seller for location"
        
        # Handle image upload
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        
        # Create product first (but don't commit yet)
        new_product = Product(
            title=title,
            description=description,
            price=price,
            condition=condition,
            contact_info=contact_info,
            image=image_filename,
            category_id=category_id,
            is_fast_moving=is_fast_moving,
            seller_id=current_user.id,
            is_active=False  # Product not active until payment confirmed
        )
        
        db.session.add(new_product)
        db.session.flush()  # Get the ID without committing
        
        # Initialize M-Pesa gateway
        mpesa = MpesaGateway()
        
        # Listing fee (you can set this in config)
        listing_fee = current_app.config.get('LISTING_FEE', 50)
        
        # Initiate M-Pesa payment
        account_reference = f"PROD{new_product.id}"
        description = f"Product listing: {title}"
        
        result, message = mpesa.stk_push(
            phone_number=phone_number,
            amount=listing_fee,
            account_reference=account_reference,
            description=description
        )
        
        if result and result.get('ResponseCode') == '0':
            # Payment initiated successfully
            checkout_request_id = result.get('CheckoutRequestID')
            merchant_request_id = result.get('MerchantRequestID')
            
            # Create payment record (we'll add this to models)
            from app.models import Payment
            payment = Payment(
                product_id=new_product.id,
                user_id=current_user.id,
                amount=listing_fee,
                phone_number=phone_number,
                checkout_request_id=checkout_request_id,
                merchant_request_id=merchant_request_id,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            flash('M-Pesa payment initiated! Check your phone to complete the payment.', 'success')
            return render_template('products/payment_pending.html', 
                                product=new_product,
                                checkout_request_id=checkout_request_id)
        else:
            # Payment failed to initiate
            db.session.rollback()
            error_message = result.get('errorMessage', 'Failed to initiate payment') if result else message
            flash(f'Payment failed: {error_message}', 'error')
            return redirect(url_for('products.create_product'))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Payment error: {str(e)}")
        flash('An error occurred during payment. Please try again.', 'error')
        return redirect(url_for('products.create_product'))

def handle_free_listing(request):
    """Handle free listing during beta testing"""
    try:
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        condition = request.form.get('condition')
        category_id = request.form.get('category_id')
        is_fast_moving = bool(request.form.get('is_fast_moving'))
        
        # Get delivery information
        delivery_option = request.form.get('delivery_option')
        contact_info = ""
        
        if delivery_option == 'free':
            contact_info = request.form.get('delivery_address', '')
        elif delivery_option == 'paid':
            delivery_fee = request.form.get('delivery_fee', '0')
            contact_info = f"Paid delivery: KES {delivery_fee}"
        else:  # meetup
            contact_info = "Campus meetup - contact seller for location"
        
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
            seller_id=current_user.id,
            is_active=True  # Active immediately for free listings
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Product listed successfully! (Free during beta testing)', 'success')
        return redirect(url_for('products.my_products_list'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Free listing error: {str(e)}")
        flash('An error occurred while creating your listing. Please try again.', 'error')
        return redirect(url_for('products.create_product'))

@products_bp.route('/payment-callback', methods=['POST'])
def payment_callback():
    """Handle M-Pesa payment callback"""
    try:
        callback_data = request.get_json()
        
        if not callback_data:
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid data'})
        
        # Extract callback data
        result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        
        if result_code == 0:
            # Payment successful
            from app.models import Payment, Product
            payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
            
            if payment:
                payment.status = 'completed'
                payment.completed_at = db.func.now()
                
                # Activate the product
                product = Product.query.get(payment.product_id)
                if product:
                    product.is_active = True
                
                db.session.commit()
                
                current_app.logger.info(f"Payment completed for product {payment.product_id}")
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})
        
    except Exception as e:
        current_app.logger.error(f"Callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error'})

@products_bp.route('/check-payment-status/<checkout_request_id>')
@login_required
def check_payment_status(checkout_request_id):
    """Check payment status for a pending payment"""
    from app.models import Payment
    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
    
    if not payment:
        return jsonify({'status': 'not_found'})
    
    if payment.status == 'completed':
        return jsonify({
            'status': 'completed',
            'product_id': payment.product_id
        })
    elif payment.status == 'pending':
        # Check with M-Pesa
        mpesa = MpesaGateway()
        status_result = mpesa.check_transaction_status(checkout_request_id)
        
        if status_result and status_result.get('ResultCode') == 0:
            payment.status = 'completed'
            payment.completed_at = db.func.now()
            
            # Activate product
            product = Product.query.get(payment.product_id)
            if product:
                product.is_active = True
            
            db.session.commit()
            return jsonify({'status': 'completed', 'product_id': payment.product_id})
    
    return jsonify({'status': 'pending'})

# Keep your existing routes (they remain the same)
@products_bp.route('/my-products')
@login_required
def my_products_list():
    products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('products/my_products.html', products=products, categories=categories)

@products_bp.route('/all')
def all_products():
    products = Product.query.filter_by(is_sold=False, is_active=True).order_by(Product.created_at.desc()).all()
    return render_template('products/all.html', products=products)

@products_bp.route('/view/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    has_paid = True
    return render_template('products/view.html', product=product, has_paid=has_paid)

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        flash('You can only edit your own products!', 'error')
        return redirect(url_for('products.my_products_list'))
    
    if request.method == 'POST':
        product.title = request.form.get('title')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.condition = request.form.get('condition')
        product.category_id = request.form.get('category_id')
        product.is_fast_moving = bool(request.form.get('is_fast_moving'))
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                if product.image:
                    old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
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
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only delete your own products!'}), 403
    
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
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only mark your own products as sold!'}), 403
    
    product.is_sold = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Product marked as sold!'})