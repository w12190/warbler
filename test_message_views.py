"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase
from flask_bcrypt import Bcrypt

from models import db, connect_db, Message, User, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False

bcrypt = Bcrypt()

class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()


        user1 = User(
            email="test@test.com",
            username="testuser",
            password=bcrypt.generate_password_hash("HASHED_PASSWORD").decode('UTF-8'),
        )
        user2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD",
        )
        self.user1 = user1
        self.user2 = user2
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        follow1 = Follows(
            user_being_followed_id = self.user1.id,
            user_following_id = self.user2.id,
            )
        self.follow1 = follow1
        db.session.add(follow1)
        db.session.commit()

    def test_add_message(self):
        """Can user add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user1.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")
    
    def test_view_follower_logged_in(self):
        """Can user view another user's profile while logged in?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        
        url = f'/users/{self.user2.id}/following'

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user1.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.get(url)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"@{self.user2.username}", resp.get_data(as_text=True))

    def test_view_follower_logged_out(self):
        """Can user NOT view another user's profile while logged out?"""

        url = f'/users/{self.user2.id}/following'
        resp = self.client.get(url)

        # Make sure it redirects
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn(f"@", resp.get_data(as_text=True))

    
    def test_add_message_logged_in(self):
        """When you’re logged in, can you add a message as yourself?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        
        url = f'/messages/new'
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.user1.id

            resp = c.post(url, data={"text": "unique test message @##$#@$"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"unique test message", resp.get_data(as_text=True)