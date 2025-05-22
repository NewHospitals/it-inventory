# ------------------- app.py -------------------
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'საიდუმლო'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

MANUFACTURERS = ['Dell', 'HP', 'Lenovo', 'Apple', 'ASUS', 'Acer', 'Samsung', 'MSI', 'Gigabyte', 'სხვა/არაბრენდი']
TYPES = ['კომპიუტერი', 'ლეპტოპი', 'მონიტორი', 'ქსელის მოწყობილობა', 'პრინტერი', 'სხვა']
STATUS_CHOICES = ['აქტიური', 'დაზიანებული', 'ჩამოწერილი', 'რეზერვში', 'გასაცემი']

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default="user")

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inv_number = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial = db.Column(db.String(100))
    status = db.Column(db.String(50))
    owner = db.Column(db.String(100))
    purchase_date = db.Column(db.String(30))
    location = db.Column(db.String(100))
    install_date = db.Column(db.String(30))
    description = db.Column(db.Text)
    comment = db.Column(db.Text)
    added_by = db.Column(db.String(100))
    last_modified = db.Column(db.String(30))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def generate_inv_number():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    latest = Item.query.order_by(Item.id.desc()).first()
    num = latest.id+1 if latest else 1
    return f"IT{prefix}-{num:04d}"

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    query = Item.query
    filters = {}
    if request.method == 'POST':
        if request.form.get('search_type'):
            query = query.filter(Item.type.like(f"%{request.form['search_type']}%"))
            filters['search_type'] = request.form['search_type']
        if request.form.get('search_manufacturer'):
            query = query.filter(Item.manufacturer.like(f"%{request.form['search_manufacturer']}%"))
            filters['search_manufacturer'] = request.form['search_manufacturer']
        if request.form.get('search_status'):
            query = query.filter(Item.status.like(f"%{request.form['search_status']}%"))
            filters['search_status'] = request.form['search_status']
        if request.form.get('search_owner'):
            query = query.filter(Item.owner.like(f"%{request.form['search_owner']}%"))
            filters['search_owner'] = request.form['search_owner']
        if request.form.get('search_serial'):
            query = query.filter(Item.serial.like(f"%{request.form['search_serial']}%"))
            filters['search_serial'] = request.form['search_serial']
    items = query.order_by(Item.id.desc()).all()
    return render_template('index.html', name=current_user.username, items=items, types=TYPES, manufacturers=MANUFACTURERS, status_choices=STATUS_CHOICES, filters=filters)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        manufacturer = request.form['manufacturer']
        if manufacturer == 'სხვა/არაბრენდი':
            manufacturer = request.form.get('other_manufacturer', 'სხვა')
        item = Item(
            inv_number=request.form['inv_number'],
            type=request.form['type'],
            manufacturer=manufacturer,
            model=request.form['model'],
            serial=request.form['serial'],
            status=request.form['status'],
            owner=request.form['owner'],
            purchase_date=request.form['purchase_date'],
            location=request.form['location'],
            install_date=request.form['install_date'],
            description=request.form['description'],
            comment=request.form['comment'],
            added_by=current_user.username,
            last_modified=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(item)
        db.session.commit()
        flash('ჩანაწერი დაემატა!')
        return redirect(url_for('index'))
    inv_number = generate_inv_number()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add.html', inv_number=inv_number, types=TYPES, manufacturers=MANUFACTURERS, status_choices=STATUS_CHOICES, today=today)

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        manufacturer = request.form['manufacturer']
        if manufacturer == 'სხვა/არაბრენდი':
            manufacturer = request.form.get('other_manufacturer', 'სხვა')
        item.inv_number = request.form['inv_number']
        item.type = request.form['type']
        item.manufacturer = manufacturer
        item.model = request.form['model']
        item.serial = request.form['serial']
        item.status = request.form['status']
        item.owner = request.form['owner']
        item.purchase_date = request.form['purchase_date']
        item.location = request.form['location']
        item.install_date = request.form['install_date']
        item.description = request.form['description']
        item.comment = request.form['comment']
        item.added_by = current_user.username
        item.last_modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.session.commit()
        flash('ჩანაწერი განახლდა!')
        return redirect(url_for('index'))
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('edit.html', item=item, types=TYPES, manufacturers=MANUFACTURERS, status_choices=STATUS_CHOICES, today=today)

@app.route('/delete/<int:item_id>')
@login_required
def delete(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('ჩანაწერი წაიშალა!')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('მომხმარებელი ან პაროლი არასწორია.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_password, role="admin")
        db.session.add(new_user)
        db.session.commit()
        flash('მომხმარებელი დარეგისტრირდა!')
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    if not os.path.exists('inventory.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
