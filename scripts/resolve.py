# SPDX-License-Identifier: MIT
"""Decide what the build workflow builds, tests and releases.

Targets: every stable CPython minor version since 3.11 that uv can install on Windows, for
x64, x86 and ARM64 (not free-threaded), plus one abi3 wheel per architecture, built with
3.11.

Every release contains the full set of wheels. Nothing is built unless a target is missing
from all of our releases (a new CPython version), or "force" is set. Our own GitHub
releases are the only state, so there is no state file to maintain.

Only the standard library is used. uv must be on PATH: the list of Pythons uv can install
is built into uv itself, so a new CPython version shows up once uv supports it.
"""

import datetime as dt
import json
import os
import re
import subprocess
import urllib.request

API = "https://api.github.com"
OLDEST = (3, 11)
ABI3_PYTHON = "3.11"
# uv's architecture name -> (our name, wheel platform tag), in build order
ARCHS = {
    "x86_64": ("x64", "win_amd64"),
    "x86": ("x86", "win32"),
    "aarch64": ("arm64", "win_arm64"),
}
STABLE = re.compile(r"(\d+)\.(\d+)\.\d+")  # not 3.16.0a2, b1, rc1


def get_json(path: str, token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pywinhook-afterlife-build-script",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_all_pages(path: str, token: str | None) -> list:
    items, page = [], 1
    PER_PAGE = 100
    while True:
        batch = get_json(f"{path}?per_page={PER_PAGE}&page={page}", token)
        items += batch
        if len(batch) < PER_PAGE:
            return items
        page += 1


def find_pythons() -> dict[tuple[int, int], set[str]]:
    """Return {(3, 11): {"x86_64", "x86", "aarch64"}, ...}: what uv can install."""
    listing = subprocess.run(
        [
            "uv",
            "python",
            "list",
            "--all-versions",
            "--all-platforms",
            "--all-arches",
            "--only-downloads",
            "--output-format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pythons: dict[tuple[int, int], set[str]] = {}
    for entry in json.loads(listing):
        # regexp comparison catches non-stable versions like 3.16.0a2
        match = STABLE.fullmatch(entry["version"])
        version = {k: int(v) for k, v in entry["version_parts"].items()}
        if not (
            match
            and entry["implementation"] == "cpython"
            and entry["os"] == "windows"
            and entry["variant"] == "default"  # not free-threaded
            and entry["arch"] in ARCHS
            and version["major"] == OLDEST[0]
            and version["minor"] >= OLDEST[1]
        ):
            continue
        pythons.setdefault((version["major"], version["minor"]), set()).add(
            entry["arch"]
        )
    return dict(sorted(pythons.items()))


def make_targets(
    pythons: dict[tuple[int, int], set[str]],
) -> tuple[list[dict], list[dict]]:
    """Return the build and test matrix entries."""
    builds, tests = [], []
    for (major, minor), uv_archs in pythons.items():
        python, cp = f"{major}.{minor}", f"cp{major}{minor}"
        for uv_arch, (arch, plat) in ARCHS.items():
            if uv_arch not in uv_archs:
                continue
            target = {
                "python": python,
                "arch": arch,
                "plat": plat,
                # What "uv venv --python" installs, e.g. cpython-3.15-windows-x86-none
                "uv_python": f"cpython-{python}-windows-{uv_arch}-none",
            }
            builds.append({**target, "abi3": False, "wheel_tag": f"{cp}-{cp}-{plat}"})
            tests.append({**target, "cp": cp})
            if python == ABI3_PYTHON:
                builds.append(
                    {**target, "abi3": True, "wheel_tag": f"{cp}-abi3-{plat}"}
                )
    return builds, tests


def find_missing(builds: list[dict], releases: list[dict]) -> list[str]:
    published = [
        asset["name"]
        for release in releases
        if not release["draft"]
        for asset in release["assets"]
    ]
    tags = [build["wheel_tag"] for build in builds]
    return [
        tag
        for tag in tags
        if not any(name.endswith(f"-{tag}.whl") for name in published)
    ]


def next_tag(today: str, existing: set[str]) -> str:
    """Return 2026-11-25, or 2026-11-25.2, .3, ... if that tag is taken."""
    tag, number = today, 1
    while tag in existing:
        number += 1
        tag = f"{today}.{number}"
    return tag


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN")
    force = os.environ.get("FORCE") == "true"
    release = os.environ.get("RELEASE") == "true"
    on_main = os.environ["GITHUB_REF"] == "refs/heads/main"

    pythons = find_pythons()
    builds, tests = make_targets(pythons)
    if not any(build["abi3"] for build in builds):
        raise ValueError(f"uv can't install CPython {ABI3_PYTHON} for Windows")

    missing = find_missing(builds, get_all_pages(f"/repos/{repo}/releases", token))
    run = force or bool(missing)
    publish = run and release and on_main

    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    refs = get_json(f"/repos/{repo}/git/matching-refs/tags/{today}", token)
    tag = next_tag(today, {ref["ref"].removeprefix("refs/tags/") for ref in refs})

    versions = ", ".join(f"{major}.{minor}" for major, minor in pythons)
    print("Targets:", ", ".join(build["wheel_tag"] for build in builds))
    print("Not released yet:", ", ".join(missing) or "none")
    if not run:
        print(
            "::notice::All wheels have been released already. Use 'force' to build anyway."
        )
    if release and not on_main:
        print(
            "::warning::Releases are only published from main. Building without releasing."
        )

    outputs = {
        "build": json.dumps({"include": builds}, separators=(",", ":")),
        "test": json.dumps({"include": tests}, separators=(",", ":")),
        "versions": versions,
        "run": str(run).lower(),
        "publish": str(publish).lower(),
        "tag": tag,
    }
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as file:
        for key, value in outputs.items():
            file.write(f"{key}={value}\n")
            print(f"{key}={value}")


if __name__ == "__main__":
    main()
