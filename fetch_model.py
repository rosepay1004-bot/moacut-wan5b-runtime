"""Download one public, revision-pinned weight file; verify before publishing it."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import time
from urllib.request import Request, urlopen

CHUNK_BYTES = 64 * 1024 * 1024


def supports_ranges(url, size):
    request = Request(url, headers={'Range': 'bytes=0-0', 'User-Agent': 'MoaCut-model-build/340'})
    with urlopen(request, timeout=180) as source:
        return (source.status == 206 and source.headers.get('Content-Range') == f'bytes 0-0/{size}'
                and source.read(1) != b'')


def parallel_download(url, partial, size, name):
    with partial.open('xb') as output:
        output.truncate(size)
    progress = {'bytes': 0, 'reported': time.monotonic()}
    lock = threading.Lock()

    def part(start):
        end = min(start + CHUNK_BYTES, size) - 1
        request = Request(url, headers={'Range': f'bytes={start}-{end}',
                                       'User-Agent': 'MoaCut-model-build/340'})
        with urlopen(request, timeout=180) as source, partial.open('r+b') as output:
            if source.status != 206 or source.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                raise ValueError('Invalid model range response')
            output.seek(start)
            remaining = end - start + 1
            while remaining:
                block = source.read(min(4 * 1024 * 1024, remaining))
                if not block:
                    raise ValueError('Truncated model range')
                output.write(block)
                remaining -= len(block)
                with lock:
                    progress['bytes'] += len(block)
                    if time.monotonic() - progress['reported'] >= 20:
                        print(name, progress['bytes'], '/', size, '(4 connections)', flush=True)
                        progress['reported'] = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(part, range(0, size, CHUNK_BYTES)):
            pass


def fetch(index, root=Path('/opt/ComfyUI/models'), manifest_path=Path('/opt/moacut-build/models.json')):
    manifest = json.loads(manifest_path.read_text())
    item = manifest['files'][index]
    target = root / item['target']
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.part')
    url = ('https://huggingface.co/' + manifest['repository'] + '/resolve/'
           + manifest['revision'] + '/' + item['path'] + '?download=true')
    request = Request(url, headers={'User-Agent': 'MoaCut-model-build/340'})
    if item['bytes'] > CHUNK_BYTES and supports_ranges(url, item['bytes']):
        parallel_download(url, partial, item['bytes'], item['target'])
        digest, total = hashlib.sha256(), 0
        with partial.open('rb') as source:
            while block := source.read(4 * 1024 * 1024):
                total += len(block)
                digest.update(block)
        if total != item['bytes'] or digest.hexdigest() != item['sha256']:
            raise ValueError('Model checksum/size mismatch: ' + item['target'])
        partial.replace(target)
        print('VERIFIED', item['target'], total, digest.hexdigest(), flush=True)
        return
    digest, total, reported = hashlib.sha256(), 0, time.monotonic()
    with urlopen(request, timeout=180) as source, partial.open('xb') as output:
        while block := source.read(4 * 1024 * 1024):
            total += len(block)
            if total > item['bytes']:
                raise ValueError('Unexpected model size: ' + item['target'])
            output.write(block)
            digest.update(block)
            if time.monotonic() - reported >= 20:
                print(item['target'], total, '/', item['bytes'], flush=True)
                reported = time.monotonic()
    if total != item['bytes'] or digest.hexdigest() != item['sha256']:
        raise ValueError('Model checksum/size mismatch: ' + item['target'])
    partial.replace(target)
    print('VERIFIED', item['target'], total, digest.hexdigest(), flush=True)


if __name__ == '__main__':
    fetch(int(sys.argv[1]))
