#!/usr/bin/env python3

import json
import os
import sys
import time

import requests

token = os.environ["CIRCLECI_TOKEN"]

CACHE_KEY = "__cached"


def parse_time(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def api_get(
    url,
    *args,
    _version="2",
    _cache_name=None,
    _cache_filter=None,
    headers=None,
    **kwargs,
):
    fn = os.path.join("cache", _cache_name + ".json") if _cache_name else None
    if fn and os.path.exists(fn):
        with open(fn) as f:
            return {CACHE_KEY: True, **json.load(f)}
    if headers is None:
        headers = {}
    headers["Circle-Token"] = token

    while True:
        r = requests.get(
            f"https://circleci.com/api/v{_version}/{url}", *args, headers=headers, **kwargs
        )

        if r.ok:
            j = r.json()
            break

        if "Retry-After" in r.headers:
            retry_after = int(r.headers["Retry-After"])
            if retry_after > 0:
                print(f"retrying {url} after {retry_after}")
            time.sleep(retry_after)
        else:
            r.raise_for_status()

    if fn and (not _cache_filter or _cache_filter(j)):
        with open(fn, "w") as f:
            json.dump(j, f)
    return j


def api_post(url, *args, _version="2", headers=None, **kwargs):
    if headers is None:
        headers = {}
    headers["Circle-Token"] = token
    r = requests.post(
        f"https://circleci.com/api/v{_version}/{url}", *args, headers=headers, **kwargs
    )
    return r.json()


def pipelines(org_slug, page_token=None):
    return api_get(
        "pipeline", params={"org-slug": org_slug, "page-token": page_token, "mine": "false"}
    )


def project_pipelines(slug, branch, page_token=None):
    return api_get(
        f"project/{slug}/pipeline",
        params={"page-token": page_token, "branch": branch},
    )


def pipeline(slug, num):
    return api_get(f"project/{slug}/pipeline/{num}")


def pipeline_workflows(uuid, page_token=None):
    return api_get(
        f"pipeline/{uuid}/workflow",
        params={"page-token": page_token},
    )


def workflow(uuid):
    return api_get(
        f"workflow/{uuid}",
        _cache_name=f"workflow-{uuid}",
        _cache_filter=lambda r: all(r["status"] in {"success", "failed", "canceled"}),
    )


def workflow_jobs(uuid, page_token=None):
    return api_get(
        f"workflow/{uuid}/job",
        params={"page-token": page_token},
        _cache_name=f"workflow_jobs-{uuid}",
        _cache_filter=lambda r: all(
            j["status"] in {"success", "failed", "canceled"} for j in r["items"]
        ),
    )


def workflow_rerun(uuid, jobs=[], from_failed=False):
    return api_post(f"workflow/{uuid}/rerun", json={"jobs": jobs, "from_failed": from_failed})
