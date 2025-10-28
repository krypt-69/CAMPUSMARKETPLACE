from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Add sample categories
        from app.models import Category
        
        if not Category.query.first():
            categories = [
                Category(name='Electronics', description='Phones, laptops, gadgets'),
                Category(name='Furniture', description='Chairs, beds, tables'),
                Category(name='Books', description='Textbooks, novels'),
                Category(name='Other', description='Other items')
            ]
            
            for category in categories:
                db.session.add(category)
            
            db.session.commit()
            print("Sample categories added!")
    
    app.run(debug=True)