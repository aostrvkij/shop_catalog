import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from slugify import slugify
from models import db, User, Category, Product

application = Flask(__name__)
application.config['SECRET_KEY'] = 'change-me-in-production'
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
application.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
application.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

db.init_app(application)

login_manager = LoginManager(application)
login_manager.login_view = 'admin_login'

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Публичная часть ----------

@application.route('/')
def index():
    categories = Category.query.all()
    products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    return render_template('index.html', categories=categories, products=products)


@application.route('/category/<slug>')
def category_view(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    return render_template('category.html', category=category)


@application.route('/product/<int:pid>')
def product_view(pid):
    product = Product.query.get_or_404(pid)
    return render_template('product.html', product=product)


# ---------- Авторизация ----------

@application.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Неверный логин или пароль', 'error')
    return render_template('admin/login.html')


@application.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))


# ---------- Админ-панель ----------

@application.route('/admin')
@login_required
def admin_dashboard():
    stats = {
        'categories': Category.query.count(),
        'products': Product.query.count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


# Категории
@application.route('/admin/categories')
@login_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@application.route('/admin/categories/add', methods=['POST'])
@login_required
def admin_category_add():
    name = request.form['name'].strip()
    if name:
        slug = slugify(name)
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(
                name=name, slug=slug,
                description=request.form.get('description', '')
            ))
            db.session.commit()
            flash('Категория добавлена', 'success')
        else:
            flash('Такая категория уже есть', 'error')
    return redirect(url_for('admin_categories'))


@application.route('/admin/categories/<int:cid>/edit', methods=['POST'])
@login_required
def admin_category_edit(cid):
    cat = Category.query.get_or_404(cid)
    cat.name = request.form['name'].strip()
    cat.slug = slugify(cat.name)
    cat.description = request.form.get('description', '')
    db.session.commit()
    flash('Категория обновлена', 'success')
    return redirect(url_for('admin_categories'))


@application.route('/admin/categories/<int:cid>/delete', methods=['POST'])
@login_required
def admin_category_delete(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена', 'success')
    return redirect(url_for('admin_categories'))


# Товары
@application.route('/admin/products')
@login_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)


@application.route('/admin/products/add', methods=['POST'])
@login_required
def admin_product_add():
    image_name = None
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        image_name = secure_filename(file.filename)
        file.save(os.path.join(application.config['UPLOAD_FOLDER'], image_name))

    product = Product(
        name=request.form['name'].strip(),
        description=request.form.get('description', ''),
        price=float(request.form['price']),
        category_id=int(request.form['category_id']),
        image=image_name,
        in_stock='in_stock' in request.form
    )
    db.session.add(product)
    db.session.commit()
    flash('Товар добавлен', 'success')
    return redirect(url_for('admin_products'))


@application.route('/admin/products/<int:pid>/edit', methods=['POST'])
@login_required
def admin_product_edit(pid):
    p = Product.query.get_or_404(pid)
    p.name = request.form['name'].strip()
    p.description = request.form.get('description', '')
    p.price = float(request.form['price'])
    p.category_id = int(request.form['category_id'])
    p.in_stock = 'in_stock' in request.form

    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        image_name = secure_filename(file.filename)
        file.save(os.path.join(application.config['UPLOAD_FOLDER'], image_name))
        p.image = image_name

    db.session.commit()
    flash('Товар обновлён', 'success')
    return redirect(url_for('admin_products'))


@application.route('/admin/products/<int:pid>/delete', methods=['POST'])
@login_required
def admin_product_delete(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Товар удалён', 'success')
    return redirect(url_for('admin_products'))


# ---------- Инициализация ----------

def init_db():
    os.makedirs(application.config['UPLOAD_FOLDER'], exist_ok=True)
    with application.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            ))
            db.session.commit()
            print('Создан админ: admin / admin123')


if __name__ == '__main__':
    init_db()
    application.run(debug=True)