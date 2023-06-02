FROM docker.io/python:3.8-alpine

WORKDIR '/app-lib'

COPY . .

RUN pip install --no-cache-dir .

WORKDIR '/app'

ENTRYPOINT [ "python3" ]
CMD ["proxy.py"]