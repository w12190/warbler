"""Message model tests."""

import os
from datetime import datetime
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class MessageModelTestCase(TestCase):
    """Test the model for messages. """

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_message_model(self):
        """Does basic message odel work?"""

        test_time = datetime.utcnow() #might need to relocate if different from line 55

        user = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(user)
        db.session.commit()


        message = Message(
            text = "test message",
            timestamp = test_time,
            user_id = user.id
        )

        db.session.add(message)
        db.session.commit()

        # Message should have all attributes
        self.assertEqual(type(message.id), int)
        self.assertEqual(message.text, 'test message')
        self.assertEqual(message.timestamp, test_time)
        self.assertEqual(message.user_id, user.id)

    # def test_relationship(self):
    #     """ Does the relationship 