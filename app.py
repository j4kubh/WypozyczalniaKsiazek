from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# 1. Konfiguracja Bazy Danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biblioteka.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELE ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rentals = db.relationship('Rental', backref='user', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    rentals = db.relationship('Rental', backref='book', lazy=True)

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rental_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

# --- LOGIKA APLIKACJI ---

@app.route('/')
def index():
    all_books = Book.query.all()
    return render_template('index.html', books=all_books)

# Funkcja WYPOŻYCZANIA (Zmienia status na 0)
@app.route('/rent/<int:book_id>')
def rent_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.is_available:
        book.is_available = False
        db.session.commit()
    return redirect(url_for('index'))

# Funkcja ZWROTU (Zmienia status na 1) - NOWOŚĆ
@app.route('/return/<int:book_id>')
def return_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = True
    db.session.commit()
    return redirect(url_for('index'))

# Inicjalizacja danych
def setup_database():
    with app.app_context():
        db.create_all()
        if not Book.query.first():
            test_books = [
                Book(title="Wiedźmin: Ostatnie życzenie", author="Andrzej Sapkowski", image_url="https://images.unsplash.com/photo-1544947950-fa07a98d237f?q=80&w=600"),
                Book(title="Hobbit", author="J.R.R. Tolkien", image_url="https://images.unsplash.com/photo-1621351183012-e2f9972dd9bf?q=80&w=600"),
                Book(title="1984", author="George Orwell", image_url="https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=600"),
                Book(title="Mały Książę", author="Antoine de Saint-Exupéry", image_url="https://images.unsplash.com/photo-1512820790803-83ca734da794?q=80&w=600")
            ]
            db.session.bulk_save_objects(test_books)
            db.session.commit()

if __name__ == "__main__":
    setup_database()
    app.run(debug=True)