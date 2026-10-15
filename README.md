# Wan 2.2 TI2V 5B runtime

Public container recipe containing pinned ComfyUI and three checksum-verified public model files (18,144,966,705 bytes). No MoaCut application, credentials, photos, or scripts are included.

The workflow uses only the free standard public GitHub-hosted Linux runner. It aborts when disk space is insufficient. No paid GPU or larger runner is used. This builds an environment; GPU inference quality is not yet verified.

ComfyUI and Wan licenses are retained in the image. The Comfy API binds only to loopback; the consuming application must provide its own authenticated worker. Do not expose the raw API publicly.
