import os

from flask import Flask, render_template, flash, url_for, redirect, request
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, login_user, login_required, logout_user, current_user, LoginManager
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms.widgets import TextArea
import email_validator
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SECRET_KEY'] = 'PRDkkvZ3I49J2rtvGbOleSdBc6PrePlD'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(
    basedir, "data.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

bootstrap = Bootstrap5(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Length(1, 64), Email()], render_kw={"placeholder": "@"})
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)],render_kw={"placeholder": "Username"})
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('password2', message="Passwords didn't match")], render_kw={"placeholder": "Password"})
    password2 = PasswordField('Confirm password', validators=[DataRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()], render_kw={"placeholder": "@"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Password"}) 
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class NoteForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()],render_kw={"placeholder": "Title"})
    content = StringField('Content', validators=[DataRequired()], widget=TextArea(),render_kw={"placeholder": "Type in your message"})
    submit = SubmitField('Create')

class CategoryForm(FlaskForm):
    name = StringField('Category name', validators=[DataRequired()],render_kw={"placeholder": "Category name"})
    submit = SubmitField('Create')

class SearchForm(FlaskForm):
    searched = StringField('Searched', validators=[DataRequired()])
    submit = SubmitField('Search')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    notes = db.relationship('Note', backref='user')

    @property
    def password(self):
        raise AttributeError("Password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

note_category = db.Table('note_category', 
    db.Column('notes.id', db.Integer, db.ForeignKey('categories.id')),
    db.Column('categories.id', db.Integer, db.ForeignKey('notes.id'))
    )

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(500))
    content = db.Column(db.String(10000))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    categories = db.relationship('Category', secondary=note_category, backref='notes')

    def __repr__(self):
        return '<Note %r>' % self.name

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), unique=True)

    def __repr__(self):
        return '<Category %r>' % self.name

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now login.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('notes')
            return redirect(next)
        flash('Invalid username or password.')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    notes = Note.query.all()
    return render_template('notes.html', notes=notes)

@app.route('/add_note', methods=['GET', 'POST'])
@login_required
def add_note():
    form = NoteForm()
    if form.validate_on_submit():
        note = Note(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for('.notes'))
    else:
        flash('You need to login')
    return render_template('add_note.html', form=form)

@app.route('/notes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_note(id):
    note = Note.query.get_or_404(id)
    form = NoteForm()
    if form.validate_on_submit():
        note.title = form.title.data
        note.content = form.content.data
        db.session.add(note)
        db.session.commit()
        flash('The note has been updated')
        return redirect(url_for('.notes', id=note.id))
    if current_user.id == note.user_id:
        form.title.data = note.title
        form.content.data = note.content
        return render_template('edit_note.html', form=form)
    else:
        flash("You don't have a permission to edit this note")
        notes = Note.query.all()
        return render_template('notes.html', notes=notes)

@app.route('/notes/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_note(id):
    note_to_delete = Note.query.get_or_404(id)
    id = current_user.id
    if id == note_to_delete.user_id:
        try:
            db.session.delete(note_to_delete)
            db.session.commit()
            flash('Note was deleted')
            notes = Note.query.all()
            return render_template('.notes.html', notes=notes)
        except: 
            flash('There was a problem deleting note')
            notes = Note.query.all()
            return render_template('notes.html', notes=notes)
    else:
        flash("You don't have a permission to delete this note")
        notes = Note.query.all()
        return render_template('notes.html', notes=notes)


@app.route('/categories', methods=['GET', 'POST'])
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)


@app.route('/add_categories', methods=['GET', 'POST'])
@login_required
def add_categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data)
        db.session.add(category)
        db.session.commit()
        return redirect(url_for('categories'))
    else:
        flash('You need to login')
    return render_template('add_categories.html', form=form)

@app.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm()
    if form.validate_on_submit():
        category.name = form.name.data
        db.session.add(category)
        db.session.commit()
        flash('The category has been updated')
        return redirect(url_for('.categories', id=category.id))
    form.name.data = category.name
    return render_template('edit_note.html', form=form)

@app.route('/categories/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_category(id):
    category_to_delete = Category.query.get_or_404(id)
    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('Category was deleted')
        categories = Category.query.all()
        return render_template('.categories.html', categories=categories)
    except: 
        flash('There was a problem deleting note')
        categories = Category.query.all()
        return render_template('categories.html', categories=categories)

@app.route('/search', methods=['GET', 'POST'])
def search():
    q = request.args.get('q')
    if q:
        notes = Note.query.filter(Note.title.contains(q))
        return render_template('notes.html', notes=notes)
    else: 
        notes = Note.query.all()
        flash('No posts were found')
        return render_template(url_for('.notes', notes=notes))