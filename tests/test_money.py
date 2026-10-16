"""Run with python -m unittest discover -s tests -p test_money.py."""
import csv
import gc
import io
import re
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import app
import money


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.old_db = app.DB_PATH
        app.DB_PATH = Path(cls.temp.name) / 'test.db'
        app.init_db()
        with app.db_connection() as db:
            for name in ('ledger-a', 'ledger-b'):
                db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)',
                           (name, app.hash_password('test-ledger-password'), 'user', app.utc_now()))
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.BlogHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.clients = {}
        for name in ('ledger-a', 'ledger-b'):
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
            body = urllib.parse.urlencode({'username': name, 'password': 'test-ledger-password'}).encode()
            opener.open(cls.base+'/login', body).read()
            cls.clients[name] = opener

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        app.DB_PATH = cls.old_db
        gc.collect()
        cls.temp.cleanup()

    def test_amount_validation(self):
        self.assertEqual(money.amount('0.01'), 1)
        self.assertEqual(money.amount('12.30'), 1230)
        for value in ('0', '-1', '1.234', 'NaN', '1e2', '100000000'):
            with self.assertRaises(ValueError):
                money.amount(value)

    def test_full_flow_and_isolation(self):
        a, b = self.clients['ledger-a'], self.clients['ledger-b']
        self.assertIn('/login', urllib.request.urlopen(self.base+'/money').url)
        page = a.open(self.base+'/money?month=2026-10').read().decode()
        csrf = re.search('name="csrf" value="([^"]+)"', page)[1]
        bpage = b.open(self.base+'/money').read().decode()
        bcsrf = re.search('name="csrf" value="([^"]+)"', bpage)[1]
        def post(client, route, fields):
            return client.open(self.base+route, urllib.parse.urlencode(fields).encode())
        fields = dict(csrf=csrf, kind='expense', category='餐饮', amount='12.34', entry_date='2026-10-16', note='=2+3 <script>')
        page = post(a, '/money/save', fields).read().decode()
        self.assertIn('¥12.34', page)
        self.assertIn('&lt;script&gt;', page)
        with app.db_connection() as db:
            row = db.execute('SELECT * FROM money_entries').fetchone()
            entry_id = row['id']
            self.assertEqual(row['amount_fen'], 1234)
        self.assertNotIn('¥12.34', b.open(self.base+'/money?month=2026-10').read().decode())
        for route in ('/money/save', '/money/delete'):
            with self.assertRaises(urllib.error.HTTPError) as error:
                post(b, route, dict(fields, csrf=bcsrf, id=entry_id))
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as error:
            post(a, '/money/save', dict(fields, csrf='wrong'))
        self.assertEqual(error.exception.code, 403)
        exported = a.open(self.base+'/money/export?month=2026-10').read().decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(exported)))
        self.assertEqual(rows[1][2], '12.34')
        self.assertTrue(rows[1][4].startswith("'="))
        self.assertEqual(len(list(csv.reader(io.StringIO(b.open(self.base+'/money/export?month=2026-10').read().decode('utf-8-sig'))))), 1)
        filtered = a.open(self.base+'/money?month=2026-10&category='+urllib.parse.quote('工资')).read().decode()
        self.assertIn('0 笔', filtered)
        self.assertIn('¥12.34', filtered)  # Whole-month overview remains unchanged.
        other_month = a.open(self.base+'/money/export?month=2026-09').read().decode('utf-8-sig')
        self.assertEqual(len(list(csv.reader(io.StringIO(other_month)))), 1)
        with self.assertRaises(urllib.error.HTTPError) as error:
            post(a, '/money/save', dict(fields, amount='1.001', note='keep-this-note'))
        self.assertEqual(error.exception.code, 400)
        self.assertIn('keep-this-note', error.exception.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as error:
            a.open(self.base+'/money?month=2026-13')
        self.assertEqual(error.exception.code, 400)
        post(a, '/money/save', dict(fields, id=entry_id, kind='income', category='工资', amount='20.01')).read()
        with app.db_connection() as db:
            row = db.execute('SELECT * FROM money_entries').fetchone()
            self.assertEqual((row['kind'],row['amount_fen']), ('income',2001))
        post(a, '/money/delete', dict(csrf=csrf, id=entry_id, month='2026-10')).read()
        with app.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM money_entries').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
