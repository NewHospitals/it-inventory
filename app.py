import os
import io
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial = db.Column(db.String(100))
    status = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100))
    install_date = db.Column(db.String(20))
    location = db.Column(db.String(100))
    description = db.Column(db.String(255))
    comment = db.Column(db.String(255))
    added_by = db.Column(db.String(100))
    last_modified = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    filters = {
        "search_type": request.args.get("search_type", ""),
        "search_owner": request.args.get("search_owner", ""),
        "search_status": request.args.get("search_status", ""),
        "search_location": request.args.get("search_location", "")
    }
    query = Inventory.query

    if filters["search_type"]:
        query = query.filter(Inventory.type.ilike(f"%{filters['search_type']}%"))
    if filters["search_owner"]:
        query = query.filter(Inventory.owner.ilike(f"%{filters['search_owner']}%"))
    if filters["search_status"]:
        query = query.filter(Inventory.status.ilike(f"%{filters['search_status']}%"))
    if filters["search_location"]:
        query = query.filter(Inventory.location.ilike(f"%{filters['search_location']}%"))

    items = query.order_by(Inventory.id.desc()).all()
    return render_template('index.html', name=current_user.username, items=items, filters=filters)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        item = Inventory(
            type=request.form['type'],
            manufacturer=request.form.get('manufacturer', ''),
            model=request.form.get('model', ''),
            serial=request.form.get('serial', ''),
            status=request.form['status'],
            owner=request.form.get('owner', ''),
            install_date=request.form.get('install_date', ''),
            location=request.form.get('location', ''),
            description=request.form.get('description', ''),
            comment=request.form.get('comment', ''),
            added_by=current_user.username
        )
        db.session.add(item)
        db.session.commit()
        flash('ჩანაწერი წარმატებით დაემატა!')
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit(item_id):
    item = Inventory.query.get_or_404(item_id)
    if request.method == 'POST':
        item.type = request.form['type']
        item.manufacturer = request.form.get('manufacturer', '')
        item.model = request.form.get('model', '')
        item.serial = request.form.get('serial', '')
        item.status = request.form['status']
        item.owner = request.form.get('owner', '')
        item.install_date = request.form.get('install_date', '')
        item.location = request.form.get('location', '')
        item.description = request.form.get('description', '')
        item.comment = request.form.get('comment', '')
        db.session.commit()
        flash('ჩანაწერი განახლდა!')
        return redirect(url_for('index'))
    return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete(item_id):
    item = Inventory.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('ჩანაწერი წაიშალა!')
    return redirect(url_for('index'))

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_csv():
    import csv
    if request.method == 'POST':
        file = request.files['file']
        if not file or not file.filename.endswith('.csv'):
            flash('ატვირთეთ სწორი CSV ფაილი!')
            return redirect(request.url)
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        count = 0
        for row in reader:
            item = Inventory(
                type=row.get('type', ''),
                manufacturer=row.get('manufacturer', ''),
                model=row.get('model', ''),
                serial=row.get('serial', ''),
                status=row.get('status', ''),
                owner=row.get('owner', ''),
                install_date=row.get('install_date', ''),
                location=row.get('location', ''),
                description=row.get('description', ''),
                comment=row.get('comment', ''),
                added_by=current_user.username
            )
            db.session.add(item)
            count += 1
        db.session.commit()
        flash(f'{count} ჩანაწერი იმპორტირებულია!')
        return redirect(url_for('index'))
    return render_template('import.html')

@app.route('/export', methods=['GET', 'POST'])
@login_required
def export():
    import csv
    items = Inventory.query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['type','manufacturer','model','serial','status','owner','install_date','location','description','comment'])
    for i in items:
        cw.writerow([i.type, i.manufacturer, i.model, i.serial, i.status, i.owner, i.install_date, i.location, i.description, i.comment])
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename=inventory.csv"}
    )

@app.route('/download-template')
@login_required
def download_template():
    template_path = os.path.join(os.path.dirname(__file__), 'template.csv')
    return send_file(template_path, mimetype='text/csv', as_attachment=True, download_name='template.csv')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('არასწორი მონაცემები!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('ეს მომხმარებელი უკვე არსებობს!')
            return redirect(url_for('register'))
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('მომხმარებელი დარეგისტრირდა!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
