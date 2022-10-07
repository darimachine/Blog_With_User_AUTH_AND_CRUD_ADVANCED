from flask import Flask, render_template, redirect, url_for, flash,request,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donWlSihBXox7C0sKR6b'
Bootstrap(app)
ckeditor = CKEditor(app)
##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.app_context().push()
db = SQLAlchemy(app)
#gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
#login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'
login_manager.session_protection = "strong"
#DECORATOR
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous:
            return abort(403)
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function
##CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    author = relationship('Users',back_populates='posts')
    comments_post = relationship('Comment', lazy=True, backref='posts')

class Users(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False,unique=True)
    password = db.Column(db.String(80),nullable=False)
    name = db.Column(db.String(200),nullable=False)
    posts = relationship('BlogPost',lazy=True,back_populates='author')
    comments = relationship('Comment',lazy=True,backref='author')

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    #user
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    #post
    post_id = db.Column(db.Integer,db.ForeignKey('blog_posts.id'),nullable=False)

db.create_all()
@login_manager.user_loader
def load_user(user_id):
    return Users().query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=['GET','POST'])
def register():
    register_form = RegisterForm()
    if request.method == 'POST':
        if register_form.validate_on_submit():
            user = Users().query.filter_by(email=register_form.email.data).first()
            if not user:
                hasshed_pw = generate_password_hash(register_form.password.data,'pbkdf2:sha256',salt_length=6)
                new_user = Users(email=register_form.email.data,password=hasshed_pw,name=register_form.username.data)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('That Email Already Exists Try to Log In', 'error')
                return redirect(url_for('login'))
    return render_template("register.html",form=register_form)


@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = Users().query.filter_by(email=form.email.data).first()
            if user:
                password_correct=check_password_hash(user.password,form.password.data)
                if password_correct:
                    login_user(user)
                    return redirect(url_for('get_all_posts'))
                else:
                    flash('Incorrect Password','error')
                    return redirect(url_for('login'))
            else:
                flash('Incorrect Email','error')
                return redirect(url_for('login'))

    return render_template("login.html",form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if request.method == "POST" and form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(text=form.text.data,author=current_user,posts=requested_post)
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash('You need to login or register to comment','error')
            return redirect(url_for('login'))
    comment = Comment().query.all()
    print(comment)
    return render_template("post.html", post=requested_post,form=form,comments=comment)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    print(current_user)
    if request.method=='POST':
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if request.method == "POST":
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>",methods=['GET','POST'])
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)
