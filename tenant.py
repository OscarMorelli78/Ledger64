"""Local account provisioning, tenant-scoped SQLite and revocable sessions."""
import contextlib, hashlib, hmac, os, re, secrets, sqlite3, time, uuid
from pathlib import Path

ROOT=Path(os.environ.get('BC_ROOT',Path(__file__).parent/'private')).resolve()
SESSION_SECONDS=8*3600
DUMMY_SALT=b'\x00'*16

def digest(password,salt):
    return hashlib.scrypt(password.encode(),salt=salt,n=2**15,r=8,p=1,dklen=32,maxmem=64*1024*1024)

def open_db(path):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    c=sqlite3.connect(path,timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=15000')
    return c

@contextlib.contextmanager
def auth_db():
    c=open_db(ROOT/'auth.sqlite3')
    try:
        c.executescript('''CREATE TABLE IF NOT EXISTS companies(id TEXT PRIMARY KEY,name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,company TEXT NOT NULL REFERENCES companies(id),login TEXT UNIQUE NOT NULL,salt BLOB NOT NULL,password BLOB NOT NULL,role TEXT NOT NULL CHECK(role IN ('owner','analyst','reader')),enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY,start INTEGER NOT NULL,count INTEGER NOT NULL);''')
        with c:yield c
    finally:c.close()

@contextlib.contextmanager
def company_db(company):
    if not re.fullmatch(r'[a-f0-9]{32}',company):raise ValueError('Invalid company ID')
    c=open_db(ROOT/'companies'/company/'data.sqlite3')
    try:
        c.executescript('''CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,created TEXT NOT NULL,report TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,created TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,object_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,created TEXT NOT NULL,actor TEXT NOT NULL,source_hash TEXT NOT NULL,normalized_hash TEXT NOT NULL,evidence TEXT NOT NULL,report_id TEXT NOT NULL REFERENCES reports(id));''')
        with c:yield c
    finally:c.close()

def create_company(name):
    if not isinstance(name,str) or not 1<=len(name.strip())<=150:raise ValueError('Nombre inválido')
    company=uuid.uuid4().hex
    with auth_db() as c:c.execute('INSERT INTO companies VALUES(?,?)',(company,name.strip()))
    return company

def create_user(company,login,password,role='owner'):
    login=login.strip().casefold()
    if not re.fullmatch(r'[a-z0-9_.@+\-]{3,150}',login) or not 14<=len(password)<=256:raise ValueError('Usuario o contraseña inválidos (mínimo 14 caracteres)')
    salt=secrets.token_bytes(16);uid=uuid.uuid4().hex
    with auth_db() as c:c.execute('INSERT INTO users(id,company,login,salt,password,role) VALUES(?,?,?,?,?,?)',(uid,company,login,salt,digest(password,salt),role))
    return uid

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

def authenticate(login,password,ip):
    if not isinstance(login,str) or not isinstance(password,str) or len(login)>150 or len(password)>256:return None
    login=login.strip().casefold();now=int(time.time());buckets=['ip:'+ip,'login:'+login]
    with auth_db() as c:
        c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM attempts WHERE start<?',(now-900,));c.execute('DELETE FROM sessions WHERE expires<=?',(now,))
        for b in buckets:
            r=c.execute('SELECT count FROM attempts WHERE bucket=?',(b,)).fetchone()
            if r and r['count']>= (40 if b.startswith('ip:') else 8):return None
        for b in buckets:c.execute('INSERT INTO attempts VALUES(?,?,1) ON CONFLICT(bucket) DO UPDATE SET count=count+1',(b,now))
        u=c.execute('SELECT * FROM users WHERE login=?',(login,)).fetchone()
    computed=digest(password,u['salt'] if u else DUMMY_SALT)
    if not u or not hmac.compare_digest(computed,u['password']) or not u['enabled']:return None
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
    with auth_db() as c:
        # Recheck account after password computation to prevent races with revocation.
        current=c.execute('SELECT password,enabled FROM users WHERE id=?',(u['id'],)).fetchone()
        if not current or not current['enabled'] or not hmac.compare_digest(current['password'],computed):return None
        c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token_hash(token),u['id'],csrf,now+SESSION_SECONDS));c.execute('DELETE FROM attempts WHERE bucket=?',('login:'+login,))
    return token

def session(token):
    if not token or len(token)>100:return None
    with auth_db() as c:
        r=c.execute('SELECT u.id,u.company,u.role,u.login,s.csrf,c.name FROM sessions s JOIN users u ON s.user_id=u.id JOIN companies c ON c.id=u.company WHERE s.token=? AND s.expires>? AND u.enabled=1',(token_hash(token),int(time.time()))).fetchone()
    return dict(r) if r else None

def revoke(token):
    with auth_db() as c:c.execute('DELETE FROM sessions WHERE token=?',(token_hash(token),))

def disable_user(login):
    with auth_db() as c:
        c.execute('UPDATE users SET enabled=0 WHERE login=?',(login.casefold(),));c.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE login=?)',(login.casefold(),))

def reset_password(login,password):
    if not 14<=len(password)<=256:raise ValueError('Contraseña inválida (mínimo 14 caracteres)')
    salt=secrets.token_bytes(16);value=digest(password,salt)
    with auth_db() as c:
        row=c.execute('SELECT id FROM users WHERE login=?',(login.strip().casefold(),)).fetchone()
        if not row:raise ValueError('Usuario inexistente')
        c.execute('UPDATE users SET salt=?,password=? WHERE id=?',(salt,value,row['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],));c.execute('DELETE FROM attempts WHERE bucket=?',('login:'+login.strip().casefold(),))
