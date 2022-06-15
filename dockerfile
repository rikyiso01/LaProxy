FROM python

WORKDIR '/app-lib'

COPY . .

RUN pip install --no-cache-dir .

WORKDIR '/app'

CMD ["/bin/bash"]