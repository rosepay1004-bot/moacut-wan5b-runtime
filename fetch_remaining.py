"""Bounded range retry for remaining files; keep verified first-layer cache."""
from concurrent.futures import ThreadPoolExecutor
from http.client import IncompleteRead
import sys
import threading
import time
from urllib.request import Request, urlopen
import fetch_model


def parallel_download(url, partial, size, name):
    with partial.open('xb') as output:
        output.truncate(size)
    progress = {'bytes':0, 'reported':time.monotonic()}
    lock = threading.Lock()

    def part(start):
        end = min(start + fetch_model.CHUNK_BYTES, size) - 1
        cursor = start
        for attempt in range(4):
            try:
                request = Request(url, headers={'Range':f'bytes={cursor}-{end}',
                                                'User-Agent':'MoaCut-model-build/340'})
                with urlopen(request, timeout=180) as source, partial.open('r+b') as output:
                    if source.status != 206 or source.headers.get('Content-Range') != f'bytes {cursor}-{end}/{size}':
                        raise ValueError('Invalid model range response')
                    output.seek(cursor)
                    while cursor <= end:
                        block = source.read(min(4*1024*1024, end-cursor+1))
                        if not block:
                            raise OSError('Truncated model range')
                        output.write(block)
                        cursor += len(block)
                        with lock:
                            progress['bytes'] += len(block)
                            if time.monotonic() - progress['reported'] >= 20:
                                print(name, progress['bytes'], '/', size, '(4 connections)', flush=True)
                                progress['reported'] = time.monotonic()
                return
            except (OSError, IncompleteRead):
                if attempt == 3:
                    raise
                print('Retrying incomplete range', start, 'attempt', attempt+2, flush=True)
                time.sleep(2**attempt)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(part, range(0,size,fetch_model.CHUNK_BYTES)):
            pass


if __name__ == '__main__':
    fetch_model.parallel_download = parallel_download
    fetch_model.fetch(int(sys.argv[1]))
