"""Single acceptance entrypoint, no deployment or paid API calls."""
from pathlib import Path
import subprocess, sys
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, 'verify_v5.py'], cwd=root, check=True)
print('PASS: regression and HTTP/DOM checks')
subprocess.run([sys.executable,'-m','unittest','-v','test_i18n','adaptive_learning.test_learning'],cwd=root,check=True)
subprocess.run([sys.executable,'scripts/check_http_locales.py'],cwd=root,check=True)
print('PASS: nine locales, diagnostics, PDF and offline learner checks')

subprocess.run([sys.executable,'-m','unittest','-v','test_procurement','test_procurement_extensions','test_procurement_http','test_procurement_ocr','test_procurement_templates','test_procurement_fields','test_procurement_consensus','test_procurement_references','test_procurement_table'],cwd=root,check=True)
print('PASS: procurement pilot checks')
