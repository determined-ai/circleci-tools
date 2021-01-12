# coding: pyxl

import argparse
import enum
import json
import os
import queue
import re
import sys
import threading
import time
from collections import defaultdict

from pyxl import html
from pyxl.codec import parser

import circleci


for name, attrs in [
    ("svg", ["viewbox", "fill", "xmlns"]),
    ("path", ["d", "name", "fill", "fill-rule"]),
    ("g", ["name", "stroke", "stroke-width", "fill", "fill-rule"]),
    ("circle", ["name", "fill", "cx", "cy", "r"]),
    # ("animateTransform", ["attributeName", "type", "from", "to", "dur", "repeatCount"]),
]:
    globals()["x_" + name] = type(
        "x_" + name, (html.x_html_element,), {"__attrs__": {a: str for a in attrs}}
    )


def cached(enable, fn, func, *args, **kwargs):
    if enable and os.path.exists(fn):
        with open(fn) as f:
            return json.load(f)

    ret = func(*args, **kwargs)

    with open(fn, "w") as f:
        json.dump(ret, f)
    return ret


def parse_time(s):
    s = re.sub(r"(\.[0-9]+)?Z$", "", s)
    return time.strptime(s, "%Y-%m-%dT%H:%M:%S")


class SVG:
    success = <svg style="color: rgb(4, 155, 74);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M10,17 L5,12 L6.41,10.59 L10,14.17 L17.59,6.58 L19,8 L10,17 L10,17 Z"></path></svg>
    failed = <svg style="color: rgb(242, 70, 70);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M13,17 L11,17 L11,15 L13,15 L13,17 L13,17 Z M13,13 L11,13 L11,7 L13,7 L13,13 L13,13 Z"></path></svg>
    blocked = <svg style="color: rgb(127, 127, 127);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path fill-rule="evenodd" d="M2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 C6.48,2 2,6.48 2,12 Z M7,10.5 C6.17,10.5 5.5,11.17 5.5,12 C5.5,12.83 6.17,13.5 7,13.5 C7.83,13.5 8.5,12.83 8.5,12 C8.5,11.17 7.83,10.5 7,10.5 Z M17,10.5 C16.17,10.5 15.5,11.17 15.5,12 C15.5,12.83 16.17,13.5 17,13.5 C17.83,13.5 18.5,12.83 18.5,12 C18.5,11.17 17.83,10.5 17,10.5 Z M12,10.5 C11.17,10.5 10.5,11.17 10.5,12 C10.5,12.83 11.17,13.5 12,13.5 C12.83,13.5 13.5,12.83 13.5,12 C13.5,11.17 12.83,10.5 12,10.5 Z"></path></svg>
    running = <svg style="color: rgb(53, 149, 220);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><g name="icon-workflows-running" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"><circle name="Oval" fill="#3AA3F2" cx="12" cy="12" r="10"></circle><path d="M22,12 C22,6.4771525 17.5228475,2 12,2 C6.4771525,2 2,6.4771525 2,12" name="Shape" fill="#D7ECFC"></path><path d="M22,12 C22,6.4771525 17.5228475,2 12,2 C6.4771525,2 2,6.4771525 2,12" name="Shape" fill="#3AA3F2"></path></g></svg>
    on_hold = <svg style="color: rgb(166, 146, 236);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path fill-rule="evenodd" d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 Z M11,16 L9,16 L9,8 L11,8 L11,16 Z M15,16 L13,16 L13,8 L15,8 L15,16 Z"></path></svg>
    canceled = <svg style="color: rgb(127, 127, 127);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M17,13 L7,13 L7,11 L17,11 L17,13 L17,13 Z"></path></svg>


def proc(pipelines, workflows, jobs):
    structure = defaultdict(dict)

    sub_pipelines = [
        pipeline for pipeline_num, pipeline in sorted(pipelines.items(), reverse=True)
    ]

    for pipeline in sub_pipelines:
        for w in workflows[pipeline["id"]]:
            for j in jobs[w["id"]]:
                structure[w["name"]][j["name"]] = None
    doc = <html></html>
    style = """
    .rotated { vertical-align: top; transform: rotate(180deg); writing-mode: vertical-lr; min-width: 1em; }
    .icon { width: 24px; height: 24px; }
    tr:nth-of-type(n+3) td:nth-of-type(2n+3):not(.spacer) { background-color: hsl(0, 0%, 94%); }
    tr:nth-of-type(n+3) td:nth-of-type(2n+4):not(.spacer) { background-color: hsl(0, 0%, 88%); }
    """
    head = (
        <head>
        <style>
          {style}
        </style>
        </head>
    )
    body = <body></body>

    table = <table></table>
    header = <tr></tr>
    header.append(<td></td>)
    header.append(<td></td>)
    for w, js in structure.items():
        header.append(
            <th style="min-width: 2em;"></th>
        )
        header.append(
            <th style="height: 1em; min-height: 1em; text-align: center; font-size: 170%;" colspan="{len(js)}">
              <span style="position: absolute; transform: translate(-50%, 0%);">
                {w}
              </span>
            </th>
        )
    header2 = <tr></tr>
    header2.append(<td></td>)
    header2.append(<td></td>)
    for w, js in structure.items():
        header2.append(<td></td>)
        for j in js:
            header2.append(
                <td style="vertical-align: bottom; transform: rotate(45deg); transform-origin: bottom; padding-bottom: .5em;"><div class="rotated">{j}</div></td>
            )

    table.append(header)
    table.append(header2)

    for pipeline in sub_pipelines:
        row = <tr></tr>
        ts = time.strftime("%Y-%m-%d %H:%M:%S", parse_time(pipeline["created_at"]))
        branch = pipeline["vcs"].get("branch", pipeline["vcs"].get("tag", "???"))
        rev_href = f"https://github.com/determined-ai/determined/commit/{pipeline['vcs']['revision']}"
        title = pipeline["vcs"].get("commit", {}).get("subject", "")
        row.append(
            <td style="padding-right: .5em;"><b>{ts}</b></td>
        )
        row.append(
            <td style="padding-right: .5em;"><a href="{rev_href}" title="{title}">{branch}</a></td>
        )

        pipeline_workflows = {}
        statuses = {}
        for w in workflows[pipeline["id"]]:
            pipeline_workflows[w["name"]] = w
            for j in jobs[w["id"]]:
                href = (
                    (
                        f"https://app.circleci.com/pipelines/github/determined-ai/determined/{pipeline['number']}/workflows/{w['id']}/jobs/{j['job_number']}"
                    )
                    if "job_number" in j
                    else None
                )
                statuses[w["name"], j["name"]] = (
                    j["status"],
                    href,
                )

        for i, (w, js) in enumerate(structure.items()):
            time_str = ""
            if w in pipeline_workflows:
                workflow = pipeline_workflows[w]
                print(workflow)
                if workflow["created_at"] and workflow["stopped_at"]:
                    t0 = parse_time(workflow["created_at"])
                    t1 = parse_time(workflow["stopped_at"])
                    dt = int(time.mktime(t1) - time.mktime(t0))
                    h, m, s = dt // 3600, (dt % 3600) // 60, dt % 60
                    time_str = (
                        "{}:{:02}:{:02}".format(h, m, s)
                        if h
                        else "{}:{:02}".format(m, s)
                    )
            row.append(
                <td style="font-size: 90%; text-align: right; padding-left: 1em;" class="spacer">{time_str}</td>
            )

            for j in js:
                stat, href = statuses.get((w, j), ("—", None))
                if hasattr(SVG, stat):
                    stat = getattr(SVG, stat)
                else:
                    stat = stat[:2]
                if href is not None:
                    b = <a href={href}>{stat}</a>
                else:
                    b = stat

                row.append(
                    <td style="text-align: center;"><span title="{j}">{b}</span></td>
                )

        table.append(row)

    body.append(table)

    doc.append(head)
    doc.append(body)

    return doc


def worker(in_q, out_q):
    while True:
        (task, args) = in_q.get()
        if task is None:
            in_q.task_done()
            break

        if task == "pipelines":
            branch, page, token = args
            pipelines = circleci.project_pipelines(branch, page_token=token)

            for pipeline in pipelines["items"]:
                out_q.put(("pipeline", (pipeline,)))
                in_q.put(("pipeline_workflows", (pipeline,)))

            page -= 1
            if page > 0:
                in_q.put(("pipelines", (branch, page, pipelines["next_page_token"])))

        elif task == "pipeline_workflows":
            (pipeline,) = args
            workflows = circleci.pipeline_workflows(pipeline["id"])
            out_q.put(("pipeline_workflows", (pipeline, workflows["items"])))
            for workflow in workflows["items"]:
                in_q.put(("workflow_jobs", (workflow,)))

        elif task == "workflow_jobs":
            (workflow,) = args
            jobs = circleci.workflow_jobs(workflow["id"])
            out_q.put(("workflow_jobs", (workflow, jobs["items"])))

        in_q.task_done()


def proc_all(pipelines, workflows, jobs):
    def go(pipeline_filt, fn):
        sub_pipelines = {k: v for k, v in pipelines.items() if pipeline_filt(v)}
        doc = proc(sub_pipelines, workflows, jobs)
        with open(fn, "w") as f:
            print(doc, file=f)

    go(lambda p: p["vcs"].get("branch") == "master", "ci-master.html")
    go(lambda p: p["vcs"].get("branch", "").startswith("pull/"), "ci-pulls.html")
    go(lambda p: "tag" in p["vcs"], "ci-tags.html")
    go(lambda p: True, "ci-all.html")


def get_data(args):
    if args.cached:
        s = json.load(open("all-cache.json"))
        return s["pipelines"], s["workflows"], s["jobs"]

    if args.pages is None:
        args.pages = 8 if args.branch is None else 2

    pipelines_map = {}
    workflows_map = {}
    jobs_map = {}

    in_q = queue.Queue()
    out_q = queue.Queue()

    in_q.put(("pipelines", (args.branch, args.pages, None)))
    for _ in range(args.jobs):
        t = threading.Thread(target=worker, args=(in_q, out_q))
        t.daemon = True
        t.start()

    in_q.join()

    while True:
        try:
            task, ret = out_q.get_nowait()
        except queue.Empty:
            break
        if task == "pipeline":
            (pipeline,) = ret
            pipelines_map[pipeline["number"]] = pipeline
        elif task == "pipeline_workflows":
            pipeline, workflows = ret
            workflows_map[pipeline["id"]] = workflows
        elif task == "workflow_jobs":
            workflow, jobs = ret
            jobs_map[workflow["id"]] = jobs

    with open("all-cache.json", "w") as f:
        print(
            json.dumps(
                {
                    "pipelines": pipelines_map,
                    "workflows": workflows_map,
                    "jobs": jobs_map,
                },
                indent=2,
            ),
            file=f,
        )

    return pipelines_map, workflows_map, jobs_map


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", default=None, nargs="?")
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("-J", "--jobs", type=int, default=32)

    data = get_data(parser.parse_args(args))
    proc_all(*data)


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
