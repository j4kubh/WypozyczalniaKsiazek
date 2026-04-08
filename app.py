from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURACJA ---
app.config['SECRET_KEY'] = 'twoj-bardzo-tajny-klucz' # Ważne dla sesji!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biblioteka.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- OBSŁUGA LOGOWANIA ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Gdzie przekierować, gdy ktoś nie jest zalogowany

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MODELE ---

# Dodajemy UserMixin, aby Flask-Login wiedział jak obsługiwać użytkownika
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) # Dodaliśmy pole na hasło
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

# REJESTRACJA
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password') # Pobieramy drugie hasło
        
        # 1. Sprawdzenie czy hasła są identyczne
        if password != confirm_password:
            flash('Hasła nie są identyczne!', 'danger')
            return redirect(url_for('register'))

        # 2. Sprawdzenie czy użytkownik już istnieje
        if User.query.filter_by(username=username).first():
            flash('Użytkownik o tej nazwie już istnieje!', 'danger')
            return redirect(url_for('register'))
        
        # 3. Szyfrowanie i zapis
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Konto założone! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# LOGOWANIE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Błędne dane logowania!', 'danger')
            
    return render_template('login.html')

# WYLOGOWANIE
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# WYPOŻYCZANIE (Tylko dla zalogowanych)
@app.route('/rent/<int:book_id>')
@login_required
def rent_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.is_available:
        book.is_available = False
        # Tworzymy rekord w tabeli Rental
        new_rental = Rental(user_id=current_user.id, book_id=book.id)
        db.session.add(new_rental)
        db.session.commit()
        flash(f'Wypożyczyłeś książkę: {book.title}', 'success')
    return redirect(url_for('index'))

# ZWROT
@app.route('/return/<int:book_id>')
@login_required
def return_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = True
    
    # Znajdź aktywny rekord wypożyczenia i ustaw datę zwrotu
    rental = Rental.query.filter_by(book_id=book.id, return_date=None).first()
    if rental:
        rental.return_date = datetime.utcnow()
        
    db.session.commit()
    flash(f'Zwróciłeś książkę: {book.title}', 'info')
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



            # WIDOK DODAWANIA KSIĄŻEK (ADMIN)
# WIDOK DODAWANIA KSIĄŻEK (TYLKO DLA ADMINA)
@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_book():
    # Sprawdzamy, czy zalogowany użytkownik ma nick "admin"
    if current_user.username != 'admin':
        flash('Brak uprawnień! Tylko administrator może dodawać książki.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        image_url = request.form.get('image_url')
        
        new_book = Book(
            title=title, 
            author=author, 
            image_url=image_url, 
            is_available=True
        )
        
        db.session.add(new_book)
        db.session.commit()
        flash(f'Książka "{title}" została pomyślnie dodana!', 'success')
        return redirect(url_for('index'))
        
    return render_template('add_book.html')

if __name__ == "__main__":
    setup_database()
    app.run(debug=True)