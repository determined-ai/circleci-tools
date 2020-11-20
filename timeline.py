#!/usr/bin/env python3

from typing import List, NamedTuple
import json
import os
import sys
import time

from matplotlib import pyplot as plt
import matplotlib
import requests

token = os.environ["CIRCLECI_TOKEN"]


def parse_time(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


class Job(NamedTuple):
    id: str
    name: str
    start: float
    stop: float
    status: str
    dependencies: List[str]

    @staticmethod
    def from_json(j):
        return Job(
            id=j["id"],
            name=j["name"],
            start=parse_time(j["started_at"]),
            stop=parse_time(j["stopped_at"]),
            status=j["status"],
            dependencies=j["dependencies"],
        )


def api_get(url, *args, headers=None, **kwargs):
    if headers is None:
        headers = {}
    headers["Circle-Token"] = token
    return requests.get(
        "https://circleci.com/api/v2/" + url, *args, headers=headers, **kwargs
    )


def main(args):
    workflow_id = args[0]
    fn = f"workflow-{workflow_id}.json"
    if os.path.exists(fn):
        with open(fn) as f:
            j = json.load(f)
    else:
        j = api_get(f"workflow/{workflow_id}/job").json()
        with open(fn, "w") as f:
            json.dump(j, f)

    jobs = [Job.from_json(x) for x in j["items"]]
    by_id = {j.id: j for j in jobs}

    parents = {
        j.id: max((by_id[d] for d in j.dependencies), key=lambda d: d.stop)
        for j in jobs
        if j.dependencies
    }

    t0 = min(x.start for x in jobs)
    t1 = max(x.stop for x in jobs)
    fig = plt.figure(figsize=(20, 6))
    ax = fig.add_subplot()
    for i, job in enumerate(jobs):
        ax.add_patch(
            matplotlib.patches.Rectangle((job.start - t0, i), job.stop - job.start, 1)
        )
        ax.text(
            (job.start + job.stop) / 2 - t0,
            i + 0.5,
            job.name,
            horizontalalignment="center",
            verticalalignment="center",
        )
    ax.set_xlim(0, t1 - t0)
    ax.set_ylim(0, len(jobs))
    ax.grid(True)
    fig.savefig("timeline.pdf")


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
