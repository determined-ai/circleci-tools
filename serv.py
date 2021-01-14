#!/usr/bin/env python3

import gzip
import sys
from types import SimpleNamespace


from flask import Flask, request, send_file

import cisummary

app = Flask(__name__)


@app.route("/master")
def master():
    pages = int(request.args.get("pages", 2))
    data = cisummary.get_data("master", pages=pages, jobs=32)
    doc = cisummary.proc(*data)
    return str(doc)


@app.after_request
def compress(r):
    if "Content-Encoding" not in r.headers:
        r.set_data(gzip.compress(r.get_data()))
        r.headers["Content-Encoding"] = "gzip"
    return r


def main(args):
    app.run(port=9999)


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
