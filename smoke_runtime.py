"""CPU-only runtime/API/codec smoke test; never loads inference weights."""
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen


def request(path, body=None):
    raw = None if body is None else json.dumps(body).encode()
    with urlopen(Request('http://127.0.0.1:8188'+path, data=raw,
                         headers={'Content-Type':'application/json'}), timeout=20) as response:
        return json.loads(response.read(4*1024*1024))


def main():
    subprocess.run([sys.executable, '/opt/moacut-build/verify_models.py'], check=True)
    with open('/tmp/cpu-smoke.log', 'wb') as log:
        process = subprocess.Popen([sys.executable, 'main.py', '--cpu', '--listen',
                                    '127.0.0.1', '--port', '8188', '--disable-auto-launch',
                                    '--disable-all-custom-nodes'], cwd='/opt/ComfyUI',
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+180
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('CPU startup failed')
                try:
                    nodes = request('/object_info')
                    break
                except OSError:
                    time.sleep(2)
            else:
                raise RuntimeError('CPU startup timed out')
            required = ('UNETLoader', 'CLIPLoader', 'VAELoader', 'ModelSamplingSD3',
                        'Wan22ImageToVideoLatent', 'LoadImage', 'CLIPTextEncode',
                        'KSampler', 'VAEDecode', 'CreateVideo', 'SaveVideo')
            assert all(name in nodes for name in required), 'Required node missing'
            graph = {
                '1': {'class_type':'EmptyImage', 'inputs':{'width':64, 'height':64, 'batch_size':5, 'color':0}},
                '2': {'class_type':'CreateVideo', 'inputs':{'images':['1',0], 'fps':24}},
                '3': {'class_type':'SaveVideo', 'inputs':{'video':['2',0], 'filename_prefix':'cpu_smoke', 'format':'mp4'}},
            }
            submitted = request('/prompt', {'prompt':graph})
            assert not submitted.get('node_errors'), 'Codec graph rejected'
            identity = submitted['prompt_id']
            deadline = time.monotonic()+120
            while time.monotonic() < deadline:
                history = request('/history/'+identity).get(identity)
                if history and history.get('status',{}).get('completed'):
                    assert history['status']['status_str'] == 'success', 'Codec failed'
                    item = history['outputs']['3']['images'][0]
                    output = Path('/opt/ComfyUI/output')/item['subfolder']/item['filename']
                    assert output.is_file() and output.stat().st_size > 0
                    print('CPU_SMOKE_PASS: 3 model hashes, 11 nodes, black 64x64/5-frame MP4. NOT GPU inference.', flush=True)
                    return
                time.sleep(1)
            raise RuntimeError('Codec timed out')
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
            print(Path('/tmp/cpu-smoke.log').read_text(errors='replace')[-10000:])


if __name__ == '__main__':
    main()
