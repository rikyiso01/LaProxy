FROM docker.io/python:3.8-alpine

WORKDIR '/app-lib'

COPY pyproject.toml /app-lib/pyproject.toml
COPY laproxy /app-lib/laproxy
RUN pip install --no-cache-dir .

WORKDIR '/app'

ENTRYPOINT [ "python3" ]
CMD ["proxy.py"]