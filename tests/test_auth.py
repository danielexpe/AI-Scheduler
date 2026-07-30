import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from werkzeug.security import generate_password_hash, check_password_hash


class TestPasswordHashing(unittest.TestCase):

    def test_hash_and_verify(self):
        password = "minha_senha_segura"
        hashed = generate_password_hash(password)
        self.assertTrue(check_password_hash(hashed, password))
        self.assertFalse(check_password_hash(hashed, "senha_errada"))

    def test_different_hashes_for_same_password(self):
        password = "senha123"
        h1 = generate_password_hash(password)
        h2 = generate_password_hash(password)
        self.assertNotEqual(h1, h2)
        self.assertTrue(check_password_hash(h1, password))
        self.assertTrue(check_password_hash(h2, password))

    def test_empty_password(self):
        hashed = generate_password_hash("")
        self.assertTrue(check_password_hash(hashed, ""))
        self.assertFalse(check_password_hash(hashed, "x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
