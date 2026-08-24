FROM public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 AS lambda-adapter
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AWS_LWA_PORT=8000 \
    AWS_LWA_READINESS_CHECK_PATH=/health
WORKDIR /workspace

COPY --from=lambda-adapter /lambda-adapter /opt/extensions/lambda-adapter
COPY pyproject.toml README.md ./
COPY services/api services/api
COPY labels.txt labels.txt
RUN pip install --no-cache-dir .

CMD ["uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8000"]
