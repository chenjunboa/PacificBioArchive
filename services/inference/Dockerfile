FROM public.ecr.aws/docker/library/python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /service

COPY services/inference/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# MegaDetector's published dependency metadata pulls in training/export tools,
# MKL, and an obsolete protobuf pin. Runtime inference only needs the packages
# above plus these import-compatible, versioned libraries.
RUN pip install --no-cache-dir pytest==8.4.1 \
    && pip install --no-cache-dir --no-deps \
    ultralytics==8.3.0 \
    yolov5==7.0.14 \
    megadetector==5.0.29
COPY services/inference/app app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
