from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
import os
from datetime import datetime
import requests
import base64
from werkzeug.utils import secure_filename
from app.models import Product, Category, Payment, ProductUnlock, User
from app import db
from app.mpesa import MpesaGateway
import uuid  # We'll create this

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
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
            image_filename = unique_filename
        
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
            
            # Create pending payment record with product data
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
            
            # Render the payment pending page with CheckoutRequestID in a way that's easy to extract
            return jsonify({
                    "status": "payment_started",
                    "checkout_request_id": checkout_request_id
                })
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



@products_bp.route('/payment-callback', methods=['POST'])
def payment_callback():
    """Handle M-Pesa payment callback"""
    try:
        callback_data = request.get_json()
        current_app.logger.info("🔔 Received M-Pesa callback: %s", callback_data)

        if not callback_data:
            current_app.logger.warning("⚠️ No callback data received.")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid data'})

        result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        current_app.logger.info(f"📦 Callback for CheckoutRequestID: {checkout_request_id}, ResultCode: {result_code}")

        payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()

        # ✅ Payment SUCCESS
        if result_code == 0:
            if payment:
                payment.status = 'completed'
                payment.completed_at = db.func.now()

                product = Product.query.get(payment.product_id)
                if product:
                    product.is_active = True

                db.session.commit()
                current_app.logger.info(f"✅ Payment confirmed & product {payment.product_id} activated.")
            else:
                current_app.logger.warning(f"⚠️ No payment found for CheckoutRequestID {checkout_request_id}")

        # ❌ Payment FAILED or CANCELLED
        else:
            if payment:
                current_app.logger.warning(f"❌ Payment failed/cancelled for CheckoutRequestID: {checkout_request_id}")
                product = Product.query.get(payment.product_id)

                # delete product if exists and still inactive
                if product and not product.is_active:
                    db.session.delete(product)
                    current_app.logger.info(f"🗑️ Deleted inactive product ID {product.id} after failed payment.")

                # delete payment record
                db.session.delete(payment)
                db.session.commit()
            else:
                current_app.logger.warning(f"⚠️ No matching payment record to clean for failed transaction.")

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})

    except Exception as e:
        current_app.logger.error(f"Callback error: {str(e)}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error'})

@products_bp.route('/check-payment-status/<checkout_request_id>')
@login_required
def check_payment_status(checkout_request_id):
    from app.models import Payment
    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
    current_app.logger.info(f"Checking payment status for {checkout_request_id}")

    if not payment:
        return jsonify({'status': 'not_found'})

    if payment.status == 'completed':
        current_app.logger.info("Payment already completed ✅")
        return jsonify({'status': 'completed', 'product_id': payment.product_id})

    elif payment.status == 'pending':
        current_app.logger.info(f"🔎 Checking M-Pesa status for {checkout_request_id}")
        mpesa = MpesaGateway()
        try:
            status_result = mpesa.check_transaction_status(checkout_request_id)
            current_app.logger.debug(f"🔁 M-Pesa Query Response: {status_result}")

            if status_result and status_result.get('ResultCode') == 0:
                payment.status = 'completed'
                payment.completed_at = db.func.now()
                product = Product.query.get(payment.product_id)
                if product:
                    product.is_active = True
                db.session.commit()
                return jsonify({'status': 'completed', 'product_id': payment.product_id})

            # if user canceled or timed out
            elif status_result and status_result.get('ResultCode') in [1032, 2001, 1]:
                current_app.logger.warning(f"❌ Payment failed or cancelled during check for {checkout_request_id}")
                payment.status = 'failed'
                db.session.commit()
                return jsonify({'status': 'failed'})

            else:
                return jsonify({'status': 'pending'})

        except Exception as e:
            current_app.logger.error(f"⚠️ Status Check Error: {str(e)}", exc_info=True)
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

@products_bp.route('/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # If user is not authenticated, redirect to login
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=url_for('products.view_product', product_id=product_id)))
    
    # Check if user is the seller - they get free access
    if product.seller_id == current_user.id:
        return render_template('products/view_product.html', product=product)
    
    # Check if user has unlocked this product
    has_unlocked = product.is_unlocked_by(current_user)
    
    if not has_unlocked:
        # Redirect to unlock/payment page
        flash('Please unlock this product to view seller details', 'info')
        return redirect(url_for('products.unlock_product', product_id=product_id))
    
    return render_template('products/view_product.html', product=product)
@products_bp.route('/payment-required/<int:product_id>')
@login_required
def payment_required(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('products/payment_required.html', product=product)

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
    try:
        product = Product.query.get_or_404(product_id)

        if product.seller_id != current_user.id:
            return jsonify({'success': False, 'message': 'You can only delete your own products!'}), 403

        # Handle image deletion safely
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if upload_folder and product.image:
            image_path = os.path.join(upload_folder, product.image)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Could not remove image file: {e}")

        db.session.delete(product)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Product deleted successfully!'})

    except Exception as e:
        current_app.logger.error(f"❌ Delete error for product {product_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Server error occurred while deleting product.'}), 500


@products_bp.route('/mark-sold/<int:product_id>', methods=['POST'])
@login_required
def mark_sold(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only mark your own products as sold!'}), 403
    
    product.is_sold = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Product marked as sold!'})

@products_bp.route("/payment-pending/<checkout_request_id>")
@login_required
def payment_pending(checkout_request_id):
    return render_template("products/payment_pending.html",
       checkout_request_id=checkout_request_id,
       product_title="Your product")
##################################################################################################################
@products_bp.route("/advpayment-pending/<checkout_request_id>")
@login_required
def advpayment_pending(checkout_request_id):
    return render_template("products/advert_payment_pending.html",
       checkout_request_id=checkout_request_id)
@products_bp.route('/product/<int:product_id>/unlock', methods=['GET', 'POST'])
@login_required
def unlock_product(product_id):
    """Initiate payment to unlock product contact details"""
    product = Product.query.get_or_404(product_id)
    
    # Check if user already unlocked this product
    existing_unlock = ProductUnlock.query.filter_by(
        product_id=product_id,
        user_id=current_user.id,
        status='completed'
    ).first()
    
    if existing_unlock:
        flash('You have already unlocked this product!', 'info')
        return redirect(url_for('products.view_product_contact', product_id=product_id))
    
    # Check if user is trying to unlock their own product
    if product.seller_id == current_user.id:
        flash('This is your own product! You can view the details.', 'info')
        return redirect(url_for('products.view_product_contact', product_id=product_id))
    
    if request.method == 'POST':
        return handle_unlock_payment(request, product)
    
    # GET request - show unlock payment page
    unlock_fee = product.get_unlock_fee()
    return render_template('products/unlock_product.html', 
                         product=product, 
                         unlock_fee=unlock_fee)

def handle_unlock_payment(request, product):
    """Handle the unlock payment process"""
    try:
        phone_number = request.form.get('mpesa_phone')
        
        # Validate phone number
        if not phone_number:
            flash('Please provide your M-Pesa phone number', 'error')
            return redirect(url_for('products.unlock_product', product_id=product.id))
        
        # Format phone number (using simple version)
        phone_number = format_phone_number_simple(phone_number)
        print(f"Formatted phone number: {phone_number}")  # Debug
        
        # Validate the formatted number
        if not phone_number or len(phone_number) != 12 or not phone_number.startswith('254'):
            flash('Please enter a valid Kenyan phone number (e.g., 0712345678)', 'error')
            return redirect(url_for('products.unlock_product', product_id=product.id))
        
        # Initialize M-Pesa gateway
        mpesa = MpesaGateway()
        
        # Get unlock fee
        unlock_fee = product.get_unlock_fee()
        print(f"Unlock fee: {unlock_fee}")  # Debug
        
        # Initiate M-Pesa STK push
        account_reference = f"UNLOCK{product.id}"
        description = f"Unlock: {product.title}"
        
        print(f"Initiating STK push for {phone_number}, amount: {unlock_fee}")  # Debug
        
        result, message = mpesa.stk_push1(
            phone_number=phone_number,
            amount=unlock_fee,
            account_reference=account_reference,
            description=description
        )
        
        print(f"STK push result: {result}")  # Debug
        print(f"STK push message: {message}")  # Debug
        
        if result and result.get('ResponseCode') == '0':
            # Payment initiated successfully
            checkout_request_id = result.get('CheckoutRequestID')
            merchant_request_id = result.get('MerchantRequestID')
            
            print(f"Payment initiated successfully. CheckoutRequestID: {checkout_request_id}")  # Debug
            
            # Create pending unlock record
            unlock = ProductUnlock(
                product_id=product.id,
                user_id=current_user.id,
                seller_id=product.seller_id,
                amount=unlock_fee,
                phone_number=phone_number,
                checkout_request_id=checkout_request_id,
                merchant_request_id=merchant_request_id,
                status='pending'
            )
            
            db.session.add(unlock)
            db.session.commit()
            
            flash('M-Pesa payment initiated! Check your phone to complete payment.', 'success')
            
            return redirect(url_for('products.payment_pending', 
                                  product_id=product.id,
                                  checkout_request_id=checkout_request_id))
            
        else:
            # Payment failed to initiate
            error_message = result.get('errorMessage', 'Failed to initiate payment') if result else message
            print(f"Payment failed: {error_message}")  # Debug
            flash(f'Payment failed: {error_message}', 'error')
            return redirect(url_for('products.unlock_product', product_id=product.id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unlock payment error: {str(e)}")
        print(f"Exception in handle_unlock_payment: {str(e)}")  # Debug
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Debug
        flash('An error occurred during payment. Please try again.', 'error')
        return redirect(url_for('products.unlock_product', product_id=product.id))

@products_bp.route('/product/<int:product_id>/contact')
@login_required
def view_product_contact(product_id):
    """View seller contact details after payment"""
    product = Product.query.get_or_404(product_id)
    seller = User.query.get(product.seller_id)
    
    # Check if user has unlocked this product or is the seller
    has_access = False
    
    if product.seller_id == current_user.id:
        has_access = True
    else:
        unlock = ProductUnlock.query.filter_by(
            product_id=product_id,
            user_id=current_user.id,
            status='completed'
        ).first()
        has_access = unlock is not None
    
    if not has_access:
        flash('Please unlock this product to view seller contact details', 'error')
        return redirect(url_for('products.unlock_product', product_id=product_id))
    
    # Mark as accessed (update unlocked_at timestamp)
    if product.seller_id != current_user.id:
        unlock = ProductUnlock.query.filter_by(
            product_id=product_id,
            user_id=current_user.id,
            status='completed'
        ).first()
        if unlock and not unlock.unlocked_at:
            unlock.unlocked_at = datetime.utcnow()
            db.session.commit()
    
    return render_template('products/product_contact.html', 
                         product=product, 
                         seller=seller)

@products_bp.route('/unlock/check-status/<checkout_request_id>')
@login_required
def check_unlock_status(checkout_request_id):
    """Check payment status for product unlock"""
    try:
        unlock = ProductUnlock.query.filter_by(
            checkout_request_id=checkout_request_id,
            user_id=current_user.id
        ).first()
        
        if not unlock:
            return jsonify({'error': 'Payment record not found'}), 404
            
        return jsonify({
            'status': unlock.status,
            'product_id': unlock.product_id,
            'mpesa_receipt': unlock.mpesa_receipt_number
        })
    except Exception as e:
        current_app.logger.error(f"Error checking unlock status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# M-Pesa Callback URL for unlock payments
@products_bp.route('/unlock/callback', methods=['POST'])
def unlock_payment_callback():
    """Handle M-Pesa callback for unlock payments"""
    try:
        callback_data = request.get_json()
        
        if not callback_data:
            current_app.logger.error("Empty unlock callback data received")
            return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"})
        
        # Log the callback for debugging
        current_app.logger.info(f"Unlock callback received: {callback_data}")
        
        # Extract callback metadata
        callback_metadata = callback_data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback_metadata.get('CheckoutRequestID')
        result_code = callback_metadata.get('ResultCode')
        
        if not checkout_request_id:
            current_app.logger.error("No CheckoutRequestID in unlock callback")
            return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"})
        
        # Find the unlock record
        unlock = ProductUnlock.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()
        
        if not unlock:
            current_app.logger.error(f"Unlock not found for CheckoutRequestID: {checkout_request_id}")
            return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"})
        
        if result_code == 0:
            # Payment successful
            callback_metadata = callback_metadata.get('CallbackMetadata', {}).get('Item', [])
            
            # Extract payment details
            mpesa_receipt_number = None
            amount = None
            phone_number = None
            
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt_number = item.get('Value')
                elif item.get('Name') == 'Amount':
                    amount = item.get('Value')
                elif item.get('Name') == 'PhoneNumber':
                    phone_number = item.get('Value')
            
            # Update unlock record
            unlock.status = 'completed'
            unlock.mpesa_receipt_number = mpesa_receipt_number
            unlock.completed_at = datetime.utcnow()
            unlock.transaction_date = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"Product unlock completed for product {unlock.product_id}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Success"})
            
        else:
            # Payment failed
            unlock.status = 'failed'
            db.session.commit()
            
            error_message = callback_metadata.get('ResultDesc', 'Payment failed')
            current_app.logger.error(f"Unlock payment failed: {error_message}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Success"})  # Always return success to M-Pesa
            
    except Exception as e:
        current_app.logger.error(f"Unlock callback processing error: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"})    


def format_phone_number(phone_number):
    """Format phone number to M-Pesa format (254...)"""
    if not phone_number:
        return None
    
    # Remove any non-digit characters except +
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different formats
    if phone_number.startswith('0'):
        # Convert 07... to 2547...
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('7'):
        # Convert 7... to 2547...
        phone_number = '254' + phone_number
    elif phone_number.startswith('254'):
        # Already in correct format
        pass
    else:
        # Assume it's already in international format
        pass
    
    # Ensure it's exactly 12 digits (254XXXXXXXXX)
    if len(phone_number) == 12 and phone_number.startswith('254'):
        return phone_number
    else:
        raise ValueError(f"Invalid phone number format: {phone_number}")

# Alternative simpler version if you prefer:
def format_phone_number_simple(phone_number):
    """Simple phone number formatter"""
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    # Convert to 254 format
    if phone_number.startswith('0'):
        return '254' + phone_number[1:]
    elif phone_number.startswith('7') and len(phone_number) == 9:
        return '254' + phone_number
    elif phone_number.startswith('254'):
        return phone_number
    else:
        # Return as is and let M-Pesa handle validation
        return phone_number
@products_bp.route('/product/<int:product_id>/contact-details', methods=['GET', 'POST'])
@login_required
def edit_contact_details(product_id):
    """Edit seller contact details for a specific product"""
    product = Product.query.get_or_404(product_id)
    
    # Check if user owns the product
    if product.seller_id != current_user.id:
        flash('You can only edit contact details for your own products', 'error')
        return redirect(url_for('products.view_product', product_id=product_id))
    
    if request.method == 'POST':
        # Update user's contact details
        current_user.phone_number = request.form.get('phone_number')
        current_user.whatsapp_number = request.form.get('whatsapp_number')
        current_user.email = request.form.get('email')
        current_user.campus_location = request.form.get('campus_location')
        current_user.hostel_name = request.form.get('hostel_name')
        current_user.hostel_room = request.form.get('hostel_room')
        current_user.contact_preference = request.form.get('contact_preference')
        
        db.session.commit()
        
        flash('Contact details updated successfully!', 'success')
        return redirect(url_for('products.view_product', product_id=product_id))
    
    return render_template('products/edit_contact_details.html', product=product)

@products_bp.route('/product/<int:product_id>/buyer-contact')
@login_required
def view_buyer_contact(product_id):
    """View seller contact details after payment (for buyers)"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if user has unlocked this product or is the seller
        if product.seller_id == current_user.id:
            # Seller viewing their own product
            return render_template('products/buyer_contact.html', 
                                 product=product, 
                                 seller=current_user)
        
        # Check if buyer has unlocked this product
        unlock = ProductUnlock.query.filter_by(
            product_id=product_id,
            user_id=current_user.id,
            status='completed'
        ).first()
        
        if not unlock:
            flash('Please unlock this product to view seller contact details', 'error')
            return redirect(url_for('products.unlock_product', product_id=product_id))
        
        # Mark as accessed
        if not unlock.unlocked_at:
            unlock.unlocked_at = datetime.utcnow()
            db.session.commit()
        
        # Get the seller - FIX: Make sure User model is imported
        seller = User.query.get(product.seller_id)
        if not seller:
            flash('Seller information not found', 'error')
            return redirect(url_for('products.view_product', product_id=product_id))
        
        return render_template('products/buyer_contact.html', 
                             product=product, 
                             seller=seller)
                             
    except Exception as e:
        current_app.logger.error(f"Error in view_buyer_contact: {str(e)}")
        flash('Error loading contact details', 'error')
        return redirect(url_for('products.view_product', product_id=product_id))