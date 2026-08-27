FROM public.ecr.aws/docker/library/python:3.12-slim

ARG FUNCTION_DIR=/function
WORKDIR ${FUNCTION_DIR}
COPY services/worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir --target ${FUNCTION_DIR} -r requirements.txt
COPY services/worker/handler.py handler.py

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["handler.lambda_handler"]
