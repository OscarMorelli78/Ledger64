"""Reproduce acceptance in separate processes, without customer data."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
for s in ['test_engine','test_ingest','test_v3','test_secure','test_hardening','test_governance','test_intelligence']:
    subprocess.run([sys.executable,'-m','unittest','-v',s],cwd=root,check=True,timeout=120)
for s in ['verify_secure_http.py','verify_intelligence_http.py']:
    subprocess.run([sys.executable,s],cwd=root,check=True,timeout=150)
