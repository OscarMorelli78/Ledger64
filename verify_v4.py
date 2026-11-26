"""Run full V4 acceptance suite using the available isolated Python environment."""
import subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
for name,modules in [('TEST_REGRESSION_V4.txt',['test_engine','test_ingest','test_v3.V3Tests','test_v3.AdditionalTests']),('TEST_SECURITY_V4.txt',['test_secure']),('TEST_HARDENING_V4.txt',['test_hardening'])]:
    p=subprocess.run([sys.executable,'-m','unittest','-v',*modules],cwd=BASE,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    log=p.stdout+p.stderr;(BASE/name).write_text(log,encoding='utf-8');print(log)
    if p.returncode:sys.exit(p.returncode)
sys.exit(subprocess.run([sys.executable,'verify_secure_http.py'],cwd=BASE,timeout=120).returncode)
