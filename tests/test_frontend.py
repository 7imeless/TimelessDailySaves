"""Production template integration: real content, account state and escaping."""
import tempfile
import gc
import unittest
from pathlib import Path

import app


class FrontendTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_db = app.DB_PATH
        app.DB_PATH = Path(self.temp.name) / 'frontend.db'
        app.init_db()
        self.token = 'frontend-test-session'
        with app.db_connection() as db:
            db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)',
                       ('frontend-admin', app.hash_password('test-password'), 'admin', app.utc_now()))
            user_id = db.execute('SELECT id FROM users WHERE username=?', ('frontend-admin',)).fetchone()[0]
            for status, slug, title in [('private', 'hidden-ui', 'PRIVATE-ONLY-TITLE'), ('published', 'escaped-ui', '<img src=x onerror=alert(1)>')]:
                db.execute('INSERT INTO articles(title,slug,category,excerpt,content,status,created_at,updated_at,published_at) VALUES (?,?,?,?,?,?,?,?,?)',
                           (title, slug, '前端', 'Real excerpt', '## Real heading\n\nReal body', status, app.utc_now(), app.utc_now(), app.utc_now()))
        self.user = app.user_by_id(user_id)
        app.SESSIONS[self.token] = {'user_id': str(user_id), 'role': 'admin', 'csrf': 'test-csrf'}

    def tearDown(self):
        app.SESSIONS.pop(self.token, None)
        app.DB_PATH = self.previous_db
        gc.collect()
        self.temp.cleanup()

    def test_server_content_and_private_visibility(self):
        guest = app.homepage()
        self.assertIn('/post/escaped-ui', guest)
        self.assertNotIn('PRIVATE-ONLY-TITLE', guest)
        self.assertNotIn('<img src=x onerror=alert(1)>', guest)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', guest)
        self.assertNotIn('<!-- TOTAL -->', guest)
        self.assertNotIn('概念稿', guest)
        logged_in = app.homepage(self.user, self.token)
        self.assertIn('PRIVATE-ONLY-TITLE', logged_in)
        self.assertIn('frontend-admin', logged_in)
        self.assertIn('name="csrf" value="test-csrf"', logged_in)
        archive = app.archive_page(self.user, self.token)
        self.assertNotIn('PRIVATE-ONLY-TITLE', archive)
        self.assertIn('\\u003cimg', archive)

    def test_auth_and_article_preserve_server_features(self):
        app.set_setting('registration_mode', 'closed')
        self.assertIn('暂停注册', app.register_page())
        app.set_setting('registration_mode', 'invite')
        self.assertIn('name="invite_code"', app.register_page())
        self.assertIn('name="password_confirm"', app.register_page())
        self.assertIn('action="/login"', app.user_login_page('密码不正确'))
        self.assertIn('密码不正确', app.user_login_page('密码不正确'))
        with app.db_connection() as db:
            post = db.execute('SELECT * FROM articles WHERE slug=?', ('escaped-ui',)).fetchone()
        page = app.public_article(post, self.user, self.token)
        self.assertIn('Real body', page)
        self.assertIn('data-toc', page)
        self.assertIn('MathJax', page)
        self.assertNotIn('<img src=x onerror=alert(1)>', page)


if __name__ == '__main__':
    unittest.main()
