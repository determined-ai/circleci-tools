FROM python:3.8
COPY . /src
WORKDIR /src
RUN python -m venv /v
RUN . /v/bin/activate && pip install -r requirements.txt && mkdir cache
ENTRYPOINT ["/v/bin/python3", "serv.py"]
