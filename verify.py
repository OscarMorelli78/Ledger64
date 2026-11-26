"""Reproducible Python and Node integration tests using temporary databases."""
import os,sys,time,subprocess,tempfile,socket,urllib.request,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent

def run(args,name,env=None):
    p=subprocess.run(args,cwd=BASE,env=env,capture_output=True,text=True,timeout=120,encoding='utf-8',errors='replace');log=p.stdout+p.stderr;(BASE/name).write_text(log,encoding='utf-8');print(log);return p.returncode

def main():
    if run([sys.executable,'-m','unittest','-v','test_engine','test_ingest','test_v3.V3Tests','test_v3.AdditionalTests'],'TEST_RESULTS_V3.txt'):return 1
    node=shutil.which('node')
    if not node:print('Node.js no disponible: verificación frontend no ejecutada.');return 2
    with tempfile.TemporaryDirectory() as d:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=dict(os.environ,BC_PORT=str(port),BC_DB=str(Path(d)/'test.sqlite'),BC_TEST_URL=f'http://127.0.0.1:{port}')
        p=subprocess.Popen([sys.executable,'app.py'],cwd=BASE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(env['BC_TEST_URL'],timeout=.2).close();break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Servidor de pruebas no disponible')
            return run([node,'test_frontend.cjs'],'FRONTEND_RESULTS_V3.txt',env)
        finally:p.terminate();p.wait(timeout=10)
if __name__=='__main__':sys.exit(main())
