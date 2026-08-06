import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


class TestThemeRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def _register_and_login(self):
        import uuid
        u = f"theme_{uuid.uuid4().hex[:6]}"
        self.client.post("/auth/register", data={
            "username": u, "password": "pass1234", "confirm": "pass1234",
        }, follow_redirects=True)
        self.client.post("/auth/login", data={
            "username": u, "password": "pass1234",
        }, follow_redirects=True)
        return u

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_theme_default_on_first_visit(self):
        r = self.client.get("/auth/login")
        self.assertIn(b'data-theme="default"', r.data)

    def test_theme_toggle_to_cyberpunk(self):
        with self.client:
            r = self.client.post("/theme/toggle", data={"next": "/auth/login"},
                                 follow_redirects=True)
            self.assertEqual(r.status_code, 200)

            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get("theme"), "cyberpunk")

    def test_theme_toggle_back_to_default(self):
        with self.client:
            self.client.post("/theme/toggle", data={"next": "/auth/login"})
            self.client.post("/theme/toggle", data={"next": "/auth/login"},
                             follow_redirects=True)

            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get("theme"), "default")

    def test_theme_persists_across_pages(self):
        with self.client:
            self.client.post("/theme/toggle", data={"next": "/"})

            self._register_and_login()

            r = self.client.get("/prompts")
            self.assertIn(b'data-theme="cyberpunk"', r.data)

    def test_theme_applied_in_html(self):
        with self.client:
            self.client.post("/theme/toggle", data={"next": "/"})
            self._register_and_login()

            r = self.client.get("/")
            self.assertIn(b'data-theme="cyberpunk"', r.data)

    def test_theme_login_page_has_theme_attribute(self):
        with self.client:
            r = self.client.get("/auth/login")
            self.assertIn(b"data-theme=", r.data)

    def test_theme_redirect_back(self):
        r = self.client.post("/theme/toggle",
                             data={"next": "/prompts"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/prompts", r.headers.get("Location", ""))

    def test_theme_no_login_required(self):
        r = self.client.post("/theme/toggle", data={"next": "/"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
