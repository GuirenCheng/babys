import os
import signal
import socket
import subprocess
import sys
import time

from babys.consul import register, deregister

SERVICE = os.environ.get('SERVICE_ROLE', 'gateway')
HOST = socket.gethostname()  # 容器 hostname，即服务实例对外地址
PORT = int(os.environ.get('PORT', '8000'))
SERVICE_ID = os.environ.get('SERVICE_ID', f'{SERVICE}-{HOST}')

GUNICORN_CMD = [
    'gunicorn', 'babys.wsgi:application',
    '--bind', f'0.0.0.0:{PORT}',
    '--workers', os.environ.get('GUNICORN_WORKERS', '2'),
    '--timeout', '60',
]

proc = None
_shutdown = False


def _handle(signum, frame):
    global _shutdown
    _shutdown = True
    if proc and proc.poll() is None:
        proc.send_signal(signum)


signal.signal(signal.SIGTERM, _handle)
signal.signal(signal.SIGINT, _handle)


def _register_with_retry():
    for attempt in range(10):
        try:
            register(SERVICE, SERVICE_ID, HOST, PORT)
            print(f'[consul] 注册成功 {SERVICE_ID} -> {SERVICE} {HOST}:{PORT}', flush=True)
            return True
        except Exception as e:
            print(f'[consul] 注册失败(重试 {attempt + 1}/10): {e}', flush=True)
            time.sleep(2)
    return False


if __name__ == '__main__':
    _register_with_retry()
    proc = subprocess.Popen(GUNICORN_CMD)
    try:
        while proc.poll() is None and not _shutdown:
            time.sleep(1)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        deregister(SERVICE_ID)
        print(f'[consul] 注销 {SERVICE_ID}', flush=True)
        sys.exit(proc.returncode if proc.returncode is not None else 0)
