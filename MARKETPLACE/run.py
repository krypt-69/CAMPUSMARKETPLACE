# run.py
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        try:
            
            # Drop all tables and recreate (for development only)
            print("Database tables  not created!")
            
            # Add sample categories
            from app.models import Category
            
            categories = [
                Category(name='Electronics', description='Phones, laptops, gadgets'),
                Category(name='Furniture', description='Chairs, beds, tables'),
                Category(name='Books', description='Textbooks, novels'),
                Category(name='Other', description='Other items')
            ]
            
            for category in categories:
                db.session.add(category)
            
            db.session.commit()
            print("Database created with updated schema!")
            
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
    
    app.run(debug=True)