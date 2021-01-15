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

import circleci


for name, attrs in [
    ("svg", ["viewbox", "fill", "xmlns"]),
    ("path", ["d", "name", "fill", "fill-rule"]),
    ("g", ["name", "stroke", "stroke-width", "fill", "fill-rule"]),
    ("circle", ["name", "fill", "cx", "cy", "r"]),
    (
        "animateTransform",
        [
            "attributename",
            "calcmode",
            "type",
            "values",
            "keytimes",
            "keysplines",
            "dur",
            "repeatcount",
        ],
    ),
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


def format_duration(dt):
    h, m, s = dt // 3600, (dt % 3600) // 60, dt % 60
    return "{}:{:02}:{:02}".format(h, m, s) if h else "{}:{:02}".format(m, s)


class SVG:
    success = <svg style="color: rgb(4, 155, 74);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M10,17 L5,12 L6.41,10.59 L10,14.17 L17.59,6.58 L19,8 L10,17 L10,17 Z"></path></svg>
    failed = <svg style="color: rgb(242, 70, 70);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M13,17 L11,17 L11,15 L13,15 L13,17 L13,17 Z M13,13 L11,13 L11,7 L13,7 L13,13 L13,13 Z"></path></svg>
    blocked = <svg style="color: rgb(127, 127, 127);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path fill-rule="evenodd" d="M2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 C6.48,2 2,6.48 2,12 Z M7,10.5 C6.17,10.5 5.5,11.17 5.5,12 C5.5,12.83 6.17,13.5 7,13.5 C7.83,13.5 8.5,12.83 8.5,12 C8.5,11.17 7.83,10.5 7,10.5 Z M17,10.5 C16.17,10.5 15.5,11.17 15.5,12 C15.5,12.83 16.17,13.5 17,13.5 C17.83,13.5 18.5,12.83 18.5,12 C18.5,11.17 17.83,10.5 17,10.5 Z M12,10.5 C11.17,10.5 10.5,11.17 10.5,12 C10.5,12.83 11.17,13.5 12,13.5 C12.83,13.5 13.5,12.83 13.5,12 C13.5,11.17 12.83,10.5 12,10.5 Z"></path></svg>
    running = <svg style="color: rgb(53, 149, 220);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"> <g name="icon-workflows-running" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"> <circle name="Oval" fill="#3AA3F2" cx="12" cy="12" r="10"></circle> <path d="M22,12 C22,6.4771525 17.5228475,2 12,2 C6.4771525,2 2,6.4771525 2,12" name="Shape" fill="#D7ECFC"> <animateTransform attributeName="transform" calcMode="spline" type="rotate" values="0 12 12; 540 12 12" keyTimes="0; 1" keySplines="0.3833057108382369 0.616694289161763 0.38330571083823695 0.616694289161763" dur="4s" repeatCount="indefinite"></animateTransform> </path> <path d="M22,12 C22,6.4771525 17.5228475,2 12,2 C6.4771525,2 2,6.4771525 2,12" name="Shape" fill="#3AA3F2"> <animateTransform attributeName="transform" calcMode="spline" type="rotate" values="0 12 12; 540 12 12" keyTimes="0; 1" keySplines="0.616694289161763 0.3833057108382369 0.616694289161763 0.38330571083823695" dur="4s" repeatCount="indefinite"></animateTransform> </path> </g></svg>
    on_hold = <svg style="color: rgb(166, 146, 236);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path fill-rule="evenodd" d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 Z M11,16 L9,16 L9,8 L11,8 L11,16 Z M15,16 L13,16 L13,8 L15,8 L15,16 Z"></path></svg>
    canceled = <svg style="color: rgb(127, 127, 127);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,2 C6.48,2 2,6.48 2,12 C2,17.52 6.48,22 12,22 C17.52,22 22,17.52 22,12 C22,6.48 17.52,2 12,2 L12,2 Z M17,13 L7,13 L7,11 L17,11 L17,13 L17,13 Z"></path></svg>
    queued = <svg style="color: rgb(127, 127, 127);" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" class="icon"><path d="M12,20 C15.8659932,20 19,16.8659932 19,13 C19,9.13400675 15.8659932,6 12,6 C8.13400675,6 5,9.13400675 5,13 C5,16.8659932 8.13400675,20 12,20 Z M12,22 C7.02943725,22 3,17.9705627 3,13 C3,8.02943725 7.02943725,4 12,4 C16.9705627,4 21,8.02943725 21,13 C21,17.9705627 16.9705627,22 12,22 Z M11,1 L13,1 C13.5522847,1 14,1.44771525 14,2 C14,2.55228475 13.5522847,3 13,3 L11,3 C10.4477153,3 10,2.55228475 10,2 C10,1.44771525 10.4477153,1 11,1 Z M19.7781746,3.80761184 L21.1923882,5.22182541 C21.5829124,5.6123497 21.5829124,6.24551468 21.1923882,6.63603897 C20.8018639,7.02656326 20.1686989,7.02656326 19.7781746,6.63603897 L18.363961,5.22182541 C17.9734367,4.83130112 17.9734367,4.19813614 18.363961,3.80761184 C18.7544853,3.41708755 19.3876503,3.41708755 19.7781746,3.80761184 Z M13,9 C13,8.44771525 12.5522847,8 12,8 C11.4477153,8 11,8.44771525 11,9 L11,13 C11,13.2652165 11.1053568,13.5195704 11.2928932,13.7071068 L13.2928932,15.7071068 C13.6834175,16.0976311 14.3165825,16.0976311 14.7071068,15.7071068 C15.0976311,15.3165825 15.0976311,14.6834175 14.7071068,14.2928932 L13,12.5857864 L13,9 Z"></path></svg>


def proc(pipelines, title=None):
    structure = defaultdict(dict)

    sub_pipelines = [
        pipeline for pipeline_num, pipeline in sorted(pipelines.items(), reverse=True)
    ]

    for p in sub_pipelines:
        for w in p["workflows"]:
            for j in w["jobs"]:
                structure[w["name"]][j["name"]] = None

    try:
        # Push nightly to the end, or it'll flip back and forth depending on
        # whether the last job was a nightly or not.
        structure["nightly"] = structure.pop("nightly")
    except KeyError:
        pass

    doc = <html></html>
    style = """
    .rotated { vertical-align: top; transform: rotate(180deg); writing-mode: vertical-lr; min-width: 1em; }
    .icon { width: 24px; height: 24px; }
    tr:nth-of-type(n+3) td:nth-of-type(2n+3):not(.spacer) { background-color: hsl(0, 0%, 94%); }
    tr:nth-of-type(n+3) td:nth-of-type(2n+4):not(.spacer) { background-color: hsl(0, 0%, 88%); }
    """
    head = (
        <head>
        <title>CI summary{": " + title if title else ""}</title>
        <style>
          {style}
        </style>
        </head>
    )
    body = <body></body>

    timestamp = f"generated at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))} GMT"
    body.append(
        <div style="text-align: right;">{timestamp}</div>
    )

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

        for i, (w, js) in enumerate(structure.items()):
            time_str = ""
            time_style = "font-size: 90%; text-align: right; padding-left: 1em;"
            if w in pipeline["workflow_names"]:
                workflow = pipeline["workflow_names"][w]
                t0 = time.mktime(parse_time(workflow["created_at"]))
                if workflow["stopped_at"]:
                    t1 = time.mktime(parse_time(workflow["stopped_at"]))
                else:
                    t1 = time.mktime(time.gmtime())
                    time_style += "color: gray; font-style: italic;"
                dt = int(t1 - t0)

            row.append(
                <td style="{time_style}" class="spacer">{format_duration(dt)}</td>
            )

            for j in js:
                job = pipeline["workflow_names"].get(w, {}).get("job_names", {}).get(j)
                stat = job["status"] if job else "—"
                href = (
                    (
                        f"https://app.circleci.com/pipelines/github/determined-ai/determined/{pipeline['number']}/workflows/{workflow['id']}/jobs/{job['job_number']}"
                    )
                    if job and "job_number" in job
                    else None
                )

                if hasattr(SVG, stat):
                    stat = getattr(SVG, stat)
                else:
                    stat = stat[:2]
                if href is not None:
                    b = <a href={href}>{stat}</a>
                else:
                    b = stat

                title = j
                if job and "started_at" in job and "stopped_at" in job:
                    t0 = time.mktime(parse_time(job["started_at"]))
                    t1 = time.mktime(parse_time(job["stopped_at"]))
                    title += ": " + format_duration(int(t1 - t0))
                row.append(
                    <td style="text-align: center;"><span title="{title}">{b}</span></td>
                )

        table.append(row)

    body.append(table)

    doc.append(head)
    doc.append(body)

    return doc


def worker(in_q, out_q, pipeline_filter):
    while True:
        (task, args) = in_q.get()
        if task is None:
            in_q.task_done()
            break

        if task == "pipelines":
            branch, page, token = args
            pipelines = circleci.project_pipelines(branch, page_token=token)

            for pipeline in pipelines["items"]:
                if pipeline_filter(pipeline):
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


def proc_all(pipelines):
    def go(pipeline_filter, fn):
        doc = proc({num: p for num, p in pipelines.items() if pipeline_filter(p)})
        with open(fn, "w") as f:
            print(doc, file=f)

    go(lambda p: p["vcs"].get("branch") == "master", "ci-master.html")
    go(lambda p: p["vcs"].get("branch", "").startswith("pull/"), "ci-pulls.html")
    go(lambda p: "tag" in p["vcs"], "ci-tags.html")
    go(lambda p: True, "ci-all.html")


def get_data(branch, pages=None, cached=False, jobs=32, pipeline_filter=lambda p: True):
    if cached:
        with open("all-cache.json") as f:
            return json.load(f)

    if pages is None:
        pages = 8 if branch is None else 2

    pipelines_map = {}
    workflows_map = {}
    jobs_map = {}

    in_q = queue.Queue()
    out_q = queue.Queue()

    in_q.put(("pipelines", (branch, pages, None)))
    for _ in range(jobs):
        t = threading.Thread(
            target=worker,
            args=(in_q, out_q),
            kwargs={"pipeline_filter": pipeline_filter},
        )
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

    for num, pipeline in pipelines_map.items():
        pipeline["workflows"] = workflows_map[pipeline["id"]]
        pipeline["workflow_names"] = {
            w["name"]: w for w in workflows_map[pipeline["id"]]
        }
        for workflow in pipeline["workflows"]:
            workflow["jobs"] = jobs_map[workflow["id"]]
            workflow["job_names"] = {j["name"]: j for j in jobs_map[workflow["id"]]}

    with open("all-cache.json", "w") as f:
        json.dump(pipelines_map, f, indent=2)

    return pipelines_map


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", default=None, nargs="?")
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("-J", "--jobs", type=int, default=32)

    args = parser.parse_args(args)

    pipelines = get_data(
        args.branch, pages=args.pages, cached=args.cached, jobs=args.jobs
    )
    proc_all(pipelines)


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
