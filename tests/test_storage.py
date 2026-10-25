import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from motorlab.model import Motor
from motorlab.storage import SessionStore, Settings, SyncWorker, influx_request, line_protocol


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.temp.name) / 'telemetry.sqlite3')

    def tearDown(self):
        self.temp.cleanup()

    def test_session_csv_and_line_protocol(self):
        sid = self.store.new_session()
        point = Motor().snapshot()
        self.store.append(sid, point)
        self.assertEqual(self.store.samples(sid), [point])
        target = Path(self.temp.name) / 'out.csv'
        self.store.export(sid, target)
        with target.open() as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]['session'], sid)
        self.assertEqual(float(rows[0]['temperature']), 25)
        with self.store.connect() as db:
            row = db.execute('SELECT id,session,timestamp_ns,payload FROM samples').fetchone()
        self.assertTrue(line_protocol(row).startswith(f'motor_dc,session={sid},motor=dc_24v '))
        self.assertTrue(line_protocol(row).endswith(str(row[2])))

    def test_http_auth_retry_and_query(self):
        requests = []
        received = threading.Event()
        authorized = threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                requests.append((self.path, self.headers.get('Authorization'), body))
                self.send_response(200 if authorized.is_set() else 401)
                self.end_headers()
                if authorized.is_set():
                    self.wfile.write(b'[]')
                received.set()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        sid = self.store.new_session()
        self.store.append(sid, Motor().snapshot())
        settings = Settings(f'http://127.0.0.1:{server.server_port}', 'modelado_simulacion', 'test-token')
        worker = SyncWorker(self.store, settings)
        worker.start()
        try:
            self.assertTrue(received.wait(4), 'El trabajador no intentó sincronizar')
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT sent FROM samples').fetchone()[0], 0)
            original_body = requests[0][2]
            authorized.set()
            worker.configure(settings)
            deadline = time.monotonic()+5
            sent = 0
            while time.monotonic() < deadline:
                with self.store.connect() as db:
                    sent = db.execute('SELECT sent FROM samples').fetchone()[0]
                if sent:
                    break
                time.sleep(.02)
            self.assertEqual(sent, 1)
            writes = [r for r in requests if 'write_lp' in r[0]]
            self.assertGreaterEqual(len(writes), 2)
            self.assertEqual(writes[-1][2], original_body)
            self.assertEqual(writes[-1][1], 'Bearer test-token')
            result = influx_request(settings, '/api/v3/query_sql', json.dumps({'db': settings.database, 'q': 'SELECT 1', 'format': 'json'}).encode())
            self.assertEqual(json.loads(result), [])
        finally:
            worker.stop()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_rejects_invalid_connection(self):
        for host in ('file:///tmp/file', 'http://user:pass@localhost:8181', 'not-a-url'):
            with self.assertRaises(ValueError):
                Settings(host=host).validate()


if __name__ == '__main__':
    unittest.main()
