#!/usr/bin/env python3

from typing import List, NamedTuple
import os
import sys
import time

from matplotlib import pyplot as plt, ticker
import matplotlib

import circleci


def parse_time(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) / 60 if s else None


class Job(NamedTuple):
    id: str
    name: str
    start: float
    stop: float
    status: str
    dependencies: List[str]

    @staticmethod
    def from_json(j):
        print(j)
        return Job(
            id=j["id"],
            name=j["name"],
            start=parse_time(j["started_at"]),
            stop=parse_time(j.get("stopped_at")),
            status=j["status"],
            dependencies=j["dependencies"],
        )


def make(workflow_id, out_fn):
    jobs = [Job.from_json(x) for x in circleci.workflow_jobs(workflow_id)["items"]]
    by_id = {j.id: j for j in jobs}

    deps = {
        j.id: [by_id[d] for d in j.dependencies if by_id[d].stop]
        if j.dependencies
        else None
        for j in jobs
    }
    parents = {
        j: max(ds, key=lambda d: d.stop) if ds else None for j, ds in deps.items()
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

    t0 = min(x.start for x in jobs if x.start)
    t1 = max(x.stop for x in jobs if x.stop)
    fig = plt.figure(figsize=(20, 6))
    ax = fig.add_subplot()
    margin = 0.03
    for j, (a, b) in ranges.items():
        if j is None:
            continue
        job = by_id[j]
        if not job.stop or not job.start:
            continue
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
    # ax.set_xticks(range(0, math.ceil(t1 - t0), 2))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.set_yticks([])
    ax.grid(True, color="#333", alpha=0.4)
    ax.grid(True, color="#333", alpha=0.15, which="minor")
    fig.tight_layout()
    fig.savefig(out_fn)


def main(args):
    workflow_id = os.path.basename(args[0])
    make(workflow_id, "timeline.pdf")


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
