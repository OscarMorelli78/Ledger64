"""Start a real Uvicorn listener and run authenticated browserless UI tests."""
import os,sys,time,socket,tempfile,subprocess,urllib.request
from pathlib import Path
BASE=Path(__file__).parent
with tempfile.TemporaryDirectory() as d:
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}';env=dict(os.environ,BC_ROOT=d,BC_TLS='0',BC_ORIGIN=base,BC_TEST_URL=base)
    subprocess.run([sys.executable,'-c',"from tenant import create_company,create_user; c=create_company('Demo virtual');create_user(c,'demo-owner','Synthetic-test-password-42!')"],cwd=BASE,env=env,check=True)
    p=subprocess.Popen([sys.executable,'-m','uvicorn','secure_app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=BASE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        for _ in range(100):
            try:urllib.request.urlopen(base+'/login',timeout=.2).close();break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Servidor de pruebas no disponible')
        r=subprocess.run(['node','test_secure_frontend.cjs'],cwd=BASE,env=env,capture_output=True,text=True,timeout=100)
        log=r.stdout+r.stderr;(BASE/'FRONTEND_RESULTS_V4.txt').write_text(log);print(log);code=r.returncode
    finally:
        p.terminate();out,_=p.communicate(timeout=10);(BASE/'HTTP_SERVER_V4.txt').write_text(out)
    sys.exit(code)
