"""Offline model verification inside the final image; no network access."""
import hashlib
import json
from pathlib import Path


def verify(root=Path('/opt/ComfyUI/models'), manifest=Path('/opt/moacut-build/models.json')):
    files = json.loads(manifest.read_text())['files']
    for item in files:
        path = root/item['target']
        if not path.is_file() or path.stat().st_size != item['bytes']:
            raise ValueError('Model size mismatch: '+item['target'])
        with path.open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest() != item['sha256']:
                raise ValueError('Model checksum mismatch: '+item['target'])
        print('VERIFIED_IMAGE_MODEL',item['target'],item['bytes'],flush=True)


if __name__ == '__main__':
    verify()
