FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /service

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY services/inference/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# onnx2torch pins an obsolete ONNX release without Python 3.12 wheels. The
# runtime is compatible with current ONNX, so install it without re-resolving.
RUN pip install --no-cache-dir --no-deps onnx2torch==1.5.15
COPY services/inference/app app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
