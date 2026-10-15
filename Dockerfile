FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime@sha256:417bd75df6365104c283ea4c1651fb3530d9eb5a4c2fafa51943cff2a94e6385
ARG COMFY_REVISION=3541246a9c997f4b8c32f9f88f3c985d02021c79
LABEL org.opencontainers.image.title="MoaCut Wan 2.2 TI2V 5B runtime"
LABEL org.opencontainers.image.description="Pinned ComfyUI runtime and three verified weights; no user data or credentials."
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORKDIR /opt
ADD https://github.com/Comfy-Org/ComfyUI/archive/3541246a9c997f4b8c32f9f88f3c985d02021c79.tar.gz /tmp/comfy.tar.gz
RUN tar -xzf /tmp/comfy.tar.gz && mv ComfyUI-${COMFY_REVISION} ComfyUI && rm /tmp/comfy.tar.gz
COPY constraints.txt prepare_requirements.py /opt/moacut-build/
RUN python /opt/moacut-build/prepare_requirements.py \
    && python -m pip install -c /opt/moacut-build/constraints.txt -r /opt/moacut-build/runtime-requirements.txt \
    && python -m pip check \
    && python -m pip freeze > /opt/moacut-build/installed-requirements.txt
COPY models.json /opt/moacut-build/
COPY fetch_model.py fetch_remaining.py verify_models.py /opt/moacut-build/
RUN python /opt/moacut-build/fetch_remaining.py 0
RUN python /opt/moacut-build/fetch_remaining.py 1
RUN python /opt/moacut-build/fetch_remaining.py 2
RUN python /opt/moacut-build/verify_models.py
ADD https://raw.githubusercontent.com/Wan-Video/Wan2.2/1ea34ff48f87168174e12956e200b1d908b1c5ff/LICENSE.txt /opt/moacut-build/WAN-LICENSE
WORKDIR /opt/ComfyUI
# RunPod will override this command with MoaCut's authenticated worker bootstrap.
# Do not expose the unauthenticated Comfy API outside the container.
CMD ["python", "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-auto-launch", "--disable-all-custom-nodes"]
