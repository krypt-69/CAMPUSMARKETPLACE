from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Payment, ProductUnlock, User, Notification

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Show all active, unsold products to everyone
    all_products = Product.query.filter_by(is_active=True, is_sold=False).limit(12).all()
    fast_moving = Product.query.filter_by(is_fast_moving=True, is_sold=False).all()
    return render_template('main/index.html', 
                         all_products=all_products, 
                         fast_moving=fast_moving)

# In your main_bp routes file, add these notification routes
@main_bp.route('/notifications')
@login_required
def notification():
    """Display user notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    # Debug: Print actual notification content
    print(f"Total notifications: {notifications.total}")
    print(f"Current page: {notifications.page}")
    print(f"Total pages: {notifications.pages}")
    
    for notification in notifications.items:
        print(f"Notification {notification.id}: {notification.message} - Read: {notification.is_read}")
    
    return render_template('main/notifications.html', notifications=notifications)

@main_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('main.notifications'))
    
    notification.is_read = True
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True})
    
    flash('Notification marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True})
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/api/notifications/unread-count')
@login_required
def get_unread_count():
    """Get count of unread notifications (for AJAX requests)"""
    if current_user.is_authenticated:
        count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return jsonify({'unread_count': count})
    return jsonify({'unread_count': 0})