"""Operator-only CLI. No default credentials or self-registration."""
import argparse,getpass,os,sqlite3,hashlib,json,datetime,contextlib
from pathlib import Path
from tenant import create_company,create_user,disable_user,reset_password,ROOT,auth_db,company_db

def backup(company,dest):
    dest=Path(dest);dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    # exclusive creation, no overwrite; online backup uses SQLite snapshot
    fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        with (auth_db() if company is None else company_db(company)) as src, contextlib.closing(sqlite3.connect(dest)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup inválido')
        return hashlib.sha256(dest.read_bytes()).hexdigest()
    except BaseException:dest.unlink(missing_ok=True);raise

def restore_to_new_company(name,source):
    # Operator verifies authorization; never overwrite a live tenant.
    source=Path(source).resolve()
    with contextlib.closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup corrupto')
        tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'reports','events','reviews'}<=tables:raise ValueError('Backup no es una base V4 de empresa')
        company=create_company(name)
        with company_db(company) as dst:src.backup(dst)
        return company

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('company');x.add_argument('name')
    x=sub.add_parser('user');x.add_argument('company');x.add_argument('login');x.add_argument('--role',choices=['owner','analyst','reader'],default='owner')
    x=sub.add_parser('disable');x.add_argument('login')
    x=sub.add_parser('reset');x.add_argument('login')
    x=sub.add_parser('backup-auth');x.add_argument('destination')
    x=sub.add_parser('backup');x.add_argument('company');x.add_argument('destination')
    x=sub.add_parser('restore-new');x.add_argument('name');x.add_argument('source')
    a=p.parse_args()
    if a.cmd=='company':print(create_company(a.name))
    elif a.cmd=='user':print(create_user(a.company,a.login,getpass.getpass('Contraseña (mínimo 14 caracteres): '),a.role))
    elif a.cmd=='disable':disable_user(a.login)
    elif a.cmd=='reset':reset_password(a.login,getpass.getpass('Nueva contraseña: '))
    elif a.cmd=='backup-auth':print(backup(None,a.destination))
    elif a.cmd=='backup':print(backup(a.company,a.destination))
    elif a.cmd=='restore-new':print(restore_to_new_company(a.name,a.source))
if __name__=='__main__':main()
