import unittest
import os
from unittest.mock import MagicMock
from cogs.tickets import generate_html_transcript

class TestTickets(unittest.TestCase):
    def test_transcript_generation(self):
        msg1 = MagicMock()
        msg1.author.display_name = "User1"
        msg1.created_at.strftime.return_value = "2023-01-01 12:00:00"
        msg1.content = "Hello"

        msg2 = MagicMock()
        msg2.author.display_name = "User2"
        msg2.created_at.strftime.return_value = "2023-01-01 12:01:00"
        msg2.content = "Hi there"

        channel = MagicMock()
        channel.name = "ticket-test"

        html = generate_html_transcript(channel, [msg1, msg2])
        self.assertIn("User1", html)
        self.assertIn("Hello", html)
        self.assertIn("User2", html)
        self.assertIn("Hi there", html)
        self.assertIn("ticket-test", html)

if __name__ == '__main__':
    unittest.main()
