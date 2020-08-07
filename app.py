import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Like

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
# toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    
    if g.user:
        do_logout()
        flash("You have successfully logged out.", "success")
    else:
        flash("You're not currently logged in.", "danger")
    return redirect('/')


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>', methods = ['GET'])
def users_show(user_id):
    """Show user profile."""

    # #if POST request, toggle like status in DB using form data.
    # if request.method == 'POST': #clicked a star
    #     message_id = request.form['message_id']
    #     g_user_id = request.form['check'] #can remove this and just reference the global id

    #     current_message = Message.query.get(message_id)

    #     #if message is liked, remove like
    #     if current_message.is_liked_by(g.user, current_message): #if liked already
    #         like = Like.query.filter((Like.message_id == message_id) & (Like.user_id == g_user_id)).all()[0]
    #         db.session.delete(like)
    #         db.session.commit()
    #         return redirect(f"/users/{user_id}")

    #     #else if message is not liked, add like
    #     like = Like(user_id=g_user_id, message_id=message_id) #else if not liked already
    #     db.session.add(like)
    #     db.session.commit()
    #     return redirect(f"/users/{user_id}")

    #if GET request, display messages
    user = User.query.get_or_404(user_id)
    messages = (Message
            .query
            .filter(Message.user_id == user_id)
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect('/')
    
    user = g.user
    update_user_form = UserEditForm(obj=user)

    if update_user_form.validate_on_submit(): #if form okay (it's a POST)
        if User.authenticate(g.user.username, update_user_form.password.data): #if user authenticated ok
            user.username = update_user_form.username.data
            user.email = update_user_form.email.data
            user.image_url = update_user_form.image_url.data or "/static/images/default-pic.png"
            user.header_image_url = update_user_form.header_image_url.data or "/static/images/warbler-hero.jpg"
            user.bio = update_user_form.bio.data
            
            db.session.commit()
            return redirect(f'/users/{g.user.id}')
        else:
            flash("Incorrect password, please try again.", "danger")
    
    return render_template('/users/edit.html', form=update_user_form, user_id=user.id) #this one actually shows the page
    

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


@app.route('/users/<int:user_id>/likes')
def show_likes(user_id):
    """ Display all messages liked by a user. """
    user = User.query.get_or_404(user_id)
    #TODO: use ORM solutions instead of 'writing sql queries'
    #TODO: use count instead of len, it's faster
    #TODO: use ORM!!!!!!
    # messages = [Message.query.get(like.message_id) for like in User.query.get(user_id).likes]
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    return render_template('users/likes.html', user=user)


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")

##############################################################################
# Homepage and error pages


@app.route('/', methods=['GET'])
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

#TODO: when NOT logged in, handle case
# 1. other solution, use get and url parameters

    # #if POST, check form and update like
    # if request.method == 'POST':
    #     message_id = request.form['message_id']
    #     user_id = request.form['check']

    #     current_message = Message.query.get(message_id)

    #     if current_message.is_liked_by(g.user, current_message): #if liked already
    #         like = Like.query.filter((Like.message_id == message_id) & (Like.user_id == g.user.id)).first()
    #         db.session.delete(like)
    #         db.session.commit()
    #         return redirect('/')

    #     like = Like(user_id=user_id, message_id=message_id)
    #     db.session.add(like)
    #     db.session.commit()
    #     return redirect('/')

    #if GET, check if logged in then get user's & followed's msgs and show on homepage
    if g.user:
        follower_ids = [follower.id for follower in g.user.following]
        
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(follower_ids) | (Message.user_id == g.user.id))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())
        return render_template('home.html', messages=messages, user_id = g.user.id)
    else:
        return render_template('home-anon.html')

@app.route('/messages/<int:message_id>/like', methods=['POST'])
def add_like(message_id):
    """toggle liking a message for a logged in user
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    liked_message = Message.query.get_or_404(message_id)
    
    if liked_message in g.user.liked_messages:
        g.user.liked_messages.remove(liked_message)
    else:
        g.user.liked_messages.append(liked_message)

    db.session.commit()
        
    return redirect('/')

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
