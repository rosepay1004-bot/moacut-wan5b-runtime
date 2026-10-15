"""Omit optional example galleries/docs from the headless inference runtime."""
from pathlib import Path

OPTIONAL_UI_PACKAGES = ('comfyui-workflow-templates', 'comfyui-embedded-docs')


def runtime_requirements(text):
    return '\n'.join(line for line in text.splitlines()
                     if not line.strip().startswith(OPTIONAL_UI_PACKAGES)) + '\n'


if __name__ == '__main__':
    source = Path('/opt/ComfyUI/requirements.txt').read_text()
    Path('/opt/moacut-build/runtime-requirements.txt').write_text(runtime_requirements(source))
