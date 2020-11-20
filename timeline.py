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
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) / 60


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
        if j.dependencies
        else None
        for j in jobs
    }
    children = {j.id: [] for j in jobs}
    children[None] = []
    for j in jobs:
        p = parents[j.id]
        children[p and p.id].append(j)

    ranges = {}

    def proc(j, y):
        chs = children[j]
        if not chs:
            ranges[j] = (y, y + 1)
            y += 1
        else:
            y0 = y
            for ch in chs:
                y = proc(ch.id, y)
            ranges[j] = (y0, y)
        return y

    y1 = proc(None, 0)

    t0 = min(x.start for x in jobs)
    t1 = max(x.stop for x in jobs)
    fig = plt.figure(figsize=(20, 6))
    ax = fig.add_subplot()
    margin = 0.03
    for j, (a, b) in ranges.items():
        if j is None:
            continue
        job = by_id[j]
        ax.add_patch(
            matplotlib.patches.Rectangle(
                (job.start - t0, a + margin), job.stop - job.start, b - a - 2 * margin
            )
        )
        ax.text(
            (job.start + job.stop) / 2 - t0,
            (a + b) / 2,
            "-".join(s[:4] for s in job.name.split("-")),
            horizontalalignment="center",
            verticalalignment="center",
        )

    ax.set_xlim(0, t1 - t0)
    ax.set_ylim(0, y1)
    ax.set_xticks(range(0, int(t1 - t0), 2))
    ax.set_yticks([])
    ax.grid(True, color="#333", alpha=0.3)
    fig.tight_layout()
    fig.savefig("timeline.pdf")


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
