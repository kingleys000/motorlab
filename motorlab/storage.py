"""Sesiones locales durables y sincronización independiente con InfluxDB 3.

SQLite es el registro local y la cola de envío; InfluxDB es el destino temporal.
Cada punto conserva su timestamp para que un reintento sea idempotente.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from PySide6.QtCore import QThread, Signal

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('sim_time', 'rpm', 'current', 'temperature', 'voltage', 'load', 'cooling',
          'torque', 'power_in', 'power_out', 'power_ratio')


@dataclass(frozen=True)
class Settings:
    host: str = 'http://127.0.0.1:8181'
    database: str = 'modelado_simulacion'
    token: str = ''
    enabled: bool = True

    @classmethod
    def load(cls):
        values = {}
        path = ROOT / '.env'
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
        def get(key, default):
            return os.environ.get(key, values.get(key, default))
        return cls(
            get('INFLUX_HOST', os.getenv('INFLUXDB3_HOST_URL', cls.host)),
            get('INFLUX_DATABASE', os.getenv('INFLUXDB3_DATABASE_NAME', cls.database)),
            get('INFLUX_TOKEN', os.getenv('INFLUXDB3_AUTH_TOKEN', '')),
            get('INFLUX_ENABLED', 'true').lower() in ('true', '1', 'yes'),
        )

    def validate(self):
        parsed = urlparse(self.host)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username:
            raise ValueError('Usa una dirección http:// o https:// sin credenciales en la URL.')
        if not self.database.strip():
            raise ValueError('Indica el nombre de la base de datos.')
        if any(c in value for value in (self.host, self.database, self.token) for c in ('\n', '\r')):
            raise ValueError('La configuración no admite saltos de línea.')

    def save(self):
        self.validate()
        path = ROOT / '.env'
        # Preservar otras variables que el usuario agregue al archivo.
        existing = path.read_text().splitlines() if path.exists() else []
        keys = {'INFLUX_HOST', 'INFLUX_DATABASE', 'INFLUX_TOKEN', 'INFLUX_ENABLED'}
        lines = [line for line in existing if line.split('=', 1)[0].strip() not in keys]
        lines.extend((f'INFLUX_HOST={self.host}', f'INFLUX_DATABASE={self.database}',
                      f'INFLUX_TOKEN={self.token}', f'INFLUX_ENABLED={str(self.enabled).lower()}'))
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as out:
            out.write('\n'.join(lines) + '\n')
        path.chmod(0o600)


class SessionStore:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / 'data' / 'telemetry.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY, created TEXT NOT NULL, label TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS samples (
                  id INTEGER PRIMARY KEY, session TEXT NOT NULL,
                  timestamp_ns INTEGER NOT NULL, payload TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS samples_session ON samples(session, id);
                CREATE INDEX IF NOT EXISTS samples_sent ON samples(sent, id);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def new_session(self):
        sid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES (?, ?, ?)', (sid, now, 'Motor DC · experimento'))
        return sid

    def append(self, session, sample):
        with self.connect() as db:
            db.execute('INSERT INTO samples(session,timestamp_ns,payload) VALUES (?,?,?)',
                       (session, time.time_ns(), json.dumps(sample)))

    def sessions(self):
        with self.connect() as db:
            return db.execute('''SELECT s.id,s.created,COUNT(p.id) FROM sessions s
                LEFT JOIN samples p ON p.session=s.id GROUP BY s.id ORDER BY s.created DESC, s.rowid DESC''').fetchall()

    def samples(self, session):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                'SELECT payload FROM samples WHERE session=? ORDER BY id', (session,))]

    def export(self, session, path):
        with self.connect() as db, open(path, 'w', newline='', encoding='utf-8') as out:
            writer = csv.DictWriter(out, fieldnames=('timestamp_ns', 'session', *FIELDS))
            writer.writeheader()
            for stamp, payload in db.execute(
                    'SELECT timestamp_ns,payload FROM samples WHERE session=? ORDER BY id', (session,)):
                writer.writerow({'timestamp_ns': stamp, 'session': session, **json.loads(payload)})


def influx_request(settings, endpoint, body, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if settings.token:
        headers['Authorization'] = 'Bearer ' + settings.token
    request = Request(settings.host.rstrip('/') + endpoint, data=body, headers=headers, method='POST')
    with urlopen(request, timeout=3) as response:
        return response.read()


def line_protocol(row):
    _, session, stamp, payload = row
    fields = json.loads(payload)
    values = ','.join(f'{key}={float(fields[key]):.12g}' for key in FIELDS)
    return f'motor_dc,session={session},motor=dc_24v {values} {stamp}'


class SyncWorker(QThread):
    status = Signal(str, int)
    query_result = Signal(str)

    def __init__(self, store, settings):
        super().__init__()
        self.store, self.settings = store, settings
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.query_requested = False

    def configure(self, settings):
        with self.lock:
            self.settings = settings
        self.wake.set()

    def check(self):
        with self.lock:
            self.query_requested = True
        self.wake.set()

    def stop(self):
        self.requestInterruption()
        self.wake.set()
        self.wait(7000)

    def run(self):
        while not self.isInterruptionRequested():
            with self.lock:
                config, query = self.settings, self.query_requested
                self.query_requested = False
            count = 0
            try:
                with self.store.connect() as db:
                    count = db.execute('SELECT COUNT(*) FROM samples WHERE sent=0').fetchone()[0]
                    rows = db.execute('SELECT id,session,timestamp_ns,payload FROM samples WHERE sent=0 ORDER BY id LIMIT 500').fetchall()
                if not config.enabled:
                    self.status.emit('Modo local · sincronización desactivada', count)
                    if query:
                        self.query_result.emit('Activa InfluxDB en la configuración para consultar el servidor.')
                elif not config.token:
                    self.status.emit('InfluxDB · configura tu token', count)
                    if query:
                        self.query_result.emit('Falta el token de autenticación. Añádelo en Conectar InfluxDB.')
                else:
                    config.validate()
                    if rows:
                        endpoint = '/api/v3/write_lp?' + urlencode({'db': config.database, 'precision': 'ns', 'accept_partial': 'false'})
                        influx_request(config, endpoint, '\n'.join(map(line_protocol, rows)).encode(), 'text/plain')
                        with self.store.connect() as db:
                            db.executemany('UPDATE samples SET sent=1 WHERE id=?', [(r[0],) for r in rows])
                        count = max(0, count - len(rows))
                        self.status.emit('InfluxDB · sincronizado', count)
                    else:
                        influx_request(config, '/api/v3/query_sql', json.dumps({
                            'db': config.database, 'q': 'SELECT 1 AS connected', 'format': 'json'}).encode())
                        self.status.emit('InfluxDB · conectado', count)
                    if query:
                        result = influx_request(config, '/api/v3/query_sql', json.dumps({
                            'db': config.database, 'q': 'SELECT time, session, rpm, current, temperature FROM motor_dc ORDER BY time DESC LIMIT 10',
                            'format': 'json'}).encode())
                        self.query_result.emit(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
            except HTTPError as exc:
                message = {401: 'Token ausente o inválido', 403: 'Token sin permisos',
                           404: 'Base o ruta no encontrada'}.get(exc.code, f'El servidor respondió HTTP {exc.code}')
                self.status.emit('InfluxDB · ' + message, count)
                if query:
                    self.query_result.emit(message + '. Si aún no hay muestras, ejecuta la simulación primero.')
                exc.close()
            except (URLError, OSError, ValueError, sqlite3.Error) as exc:
                message = 'Sin conexión; datos conservados localmente'
                self.status.emit('InfluxDB · ' + message, count)
                if query:
                    self.query_result.emit(message + '. Revisa la URL, el servicio y la configuración.')
            self.wake.wait(2)
            self.wake.clear()
