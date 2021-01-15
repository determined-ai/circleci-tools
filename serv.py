#!/usr/bin/env python3

import gzip
import sys
from types import SimpleNamespace


from flask import Flask, request, send_file

import cisummary

app = Flask(__name__)

try:
    with open("secret", "rb") as f:
        secret = f.read()
except FileNotFoundError:
    print("not using secret")
else:
    print(f"using secret of {len(secret)} bytes")
    app.config["SECRET_KEY"] = secret


@app.route("/master")
def master():
    pages = int(request.args.get("pages", 2))
    data = cisummary.get_data("master", pages=pages, jobs=32)
    return str(cisummary.proc(data, title="master"))


@app.route("/pulls")
def pulls():
    pages = int(request.args.get("pages", 5))
    data = cisummary.get_data(
        None,
        pages=pages,
        jobs=32,
        pipeline_filter=lambda p: p["vcs"].get("branch", "").startswith("pull/"),
    )
    return str(cisummary.proc(data, title="pulls"))


@app.route("/tags")
def tags():
    pages = int(request.args.get("pages", 12))
    data = cisummary.get_data(
        None, pages=pages, jobs=32, pipeline_filter=lambda p: "tag" in p["vcs"]
    )
    return str(cisummary.proc(data, title="tags"))


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
