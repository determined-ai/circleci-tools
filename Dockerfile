FROM python:3.8
WORKDIR /src

RUN python -m venv /v
COPY requirements.txt .
RUN . /v/bin/activate && pip install -r requirements.txt && mkdir cache
COPY . /src
ENTRYPOINT ["/v/bin/python3", "serv.py"]
