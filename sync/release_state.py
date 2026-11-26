"""Read authenticated release state and validate provenance before reusing a draft."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ZIP = "v2ray-psh-win-x64.zip"
SUM = "SHA256SUMS.txt"
REPO = "Ktclat/v2ray-psh"
PREFIX = "<!-- v2ray-psh-build-v1: "
HEX40 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
TAG = re.compile(r"psh-v?[0-9]+(?:\.[0-9]+){1,3}-[0-9a-f]{12}-[0-9a-f]{12}")


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def lookup(tag):
    # A by-tag read can hide drafts even for authenticated clients; list is authoritative here.
    pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{REPO}/releases?per_page=100"))
    matches = [r for page in pages for r in page if r.get("tag_name") == tag]
    if len(matches) > 1:
        raise ValueError("Multiple Releases match this exact tag; inspect them before retrying")
    return matches[0] if matches else None


def checksum_line(zip_digest):
    return f"{zip_digest.removeprefix('sha256:')}  {ZIP}\n".encode("ascii")


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def manifest(tag, base, commit, tree, run_id, zip_digest):
    m = dict(tag=tag, base=base, commit=commit, tree=tree, run_id=run_id,
             zip=zip_digest, sums=digest(checksum_line(zip_digest)))
    check_manifest(m, tag, base)
    return m


def check_manifest(m, tag, base):
    if (not isinstance(m, dict) or set(m) != {"tag", "base", "commit", "tree", "run_id", "zip", "sums"}
        or m["tag"] != tag or not TAG.fullmatch(tag) or m["base"] != base
        or not all(isinstance(m[x], str) and HEX40.fullmatch(m[x]) for x in ("base", "commit", "tree"))
        or not tag.split("-")[-2] == base[:12]
        or type(m["run_id"]) is not int or m["run_id"] <= 0
        or not isinstance(m["zip"], str) or not SHA256.fullmatch(m["zip"])
        or m["sums"] != digest(checksum_line(m["zip"]))):
        raise ValueError("Invalid build provenance; leaving the draft untouched")


def extract(release, tag, base):
    notes = release.get("body") or ""
    lines = [line for line in notes.splitlines() if line.startswith(PREFIX) and line.endswith(" -->")]
    if len(lines) != 1:
        raise ValueError("Draft lacks verified build provenance; inspect the existing draft instead of replacing it")
    m = json.loads(lines[0][len(PREFIX):-4])
    check_manifest(m, tag, base)
    return m


def missing(release, m=None):
    expected = {ZIP: m["zip"], SUM: m["sums"]} if m else {ZIP: None, SUM: None}
    assets = release["assets"]
    if not isinstance(assets, list):
        raise ValueError("Invalid release asset list")
    for asset in assets:
        name = asset.get("name")
        if (name not in expected or asset.get("state") != "uploaded" or
            not isinstance(asset.get("digest"), str) or not SHA256.fullmatch(asset["digest"]) or
            (expected[name] and asset["digest"] != expected[name])):
            raise ValueError("Unexpected, incomplete or mismatching asset; no asset was deleted")
        del expected[name]
    return list(expected)


def route(release, tag, base):
    if release is None:
        return "build", None
    if release.get("tag_name") != tag or release.get("prerelease") is not True:
        raise ValueError("Unexpected release identity")
    if release.get("draft") is False:
        if missing(release):
            raise ValueError("Published release lacks expected assets; leaving it untouched")
        return "published", None
    if release.get("draft") is not True:
        raise ValueError("Unknown release state")
    m = extract(release, tag, base)
    return ("resume-files" if missing(release, m) else "resume"), m


def readback(write, read, done, allowed, attempts=3, pause=time.sleep):
    """After any uncertain write, read back before deciding whether to retry it."""
    for attempt in range(attempts):
        current = read()
        if done(current):
            return current
        allowed(current)
        try:
            write()
        except subprocess.CalledProcessError:
            pass
        # GitHub can apply a write even when its response was 5xx.
        current = read()
        if done(current):
            return current
        allowed(current)
        if attempt + 1 < attempts:
            pause(5 * (attempt + 1))
    raise ValueError("GitHub write did not take effect after readback; preserving existing draft and files")


def dispatch_allowed(event):
    if event.get("action") != "upstream-stable-release":
        return False
    p = event.get("client_payload")
    return isinstance(p, dict) and p.get("repository") == "2dust/v2rayN"


def main():
    command = sys.argv[1]
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("Wrong repository")
    if command == "dispatch":
        if not dispatch_allowed(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())):
            raise ValueError("Expected upstream-stable-release signal for 2dust/v2rayN")
        return
    tag, base = sys.argv[2:4]
    if command == "plan":
        action, m = route(lookup(tag), tag, base)
        print(json.dumps({"action": action, "manifest": m}))
        return
    if command != "publish" or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Publishing requires the default branch")
    commit, tree, run_id = sys.argv[4:7]
    directory = Path("dist")
    release = lookup(tag)
    action, old = route(release, tag, base)
    if action == "published":
        print(f"Already published: {tag}")
        return
    if old:
        if (old["commit"], old["tree"], old["run_id"]) != (commit, tree, int(run_id)):
            raise ValueError("Draft provenance differs from the checked source")
        m = old
    else:
        with (directory / ZIP).open("rb") as f:
            zip_digest = "sha256:" + hashlib.file_digest(f, "sha256").hexdigest()
        m = manifest(tag, base, commit, tree, int(run_id), zip_digest)

    def verified(r):
        if (r is None or r.get("tag_name") != tag or r.get("prerelease") is not True
            or extract(r, tag, base) != m):
            raise ValueError("Release state or provenance changed; preserving it")
        missing(r, m)
        return r

    def draft(r):
        if verified(r).get("draft") is not True:
            raise ValueError("Refusing to write assets to a published release")

    if release is None:
        notes = Path(os.environ["RUNNER_TEMP"]) / "psh-release-notes.md"
        with notes.open("a", encoding="utf-8") as f:
            f.write(f"\n{PREFIX}{json.dumps(m, separators=(',', ':'))} -->\n")
        def reserved(r):
            if r is not None:
                draft(r)
        release = readback(
            lambda: gh("release", "create", tag, "--repo", REPO, "--verify-tag", "--draft",
                       "--prerelease", "--title", f"{tag} (Windows x64)", "--notes-file", str(notes)),
            lambda: lookup(tag),
            lambda r: r is not None and verified(r).get("draft") is True,
            reserved,
        )
    release_id = release.get("id")
    if type(release_id) is not int or release_id <= 0:
        raise ValueError("Invalid GitHub Release ID")
    api = f"repos/{REPO}/releases/{release_id}"
    def latest():
        return json.loads(gh("api", api))

    present = missing(verified(release), m)
    if present:
        with (directory / ZIP).open("rb") as f:
            if "sha256:" + hashlib.file_digest(f, "sha256").hexdigest() != m["zip"]:
                raise ValueError("Original Actions artifact differs from the draft manifest")
        (directory / SUM).write_bytes(checksum_line(m["zip"]))
    for name in present:
        readback(lambda: gh("release", "upload", tag, str(directory / name), "--repo", REPO),
                 latest, lambda r: name not in missing(verified(r), m), draft)

    def completed(r):
        return verified(r).get("draft") is False and not missing(r, m)
    def ready(r):
        draft(r)
        if missing(r, m):
            raise ValueError("Cannot publish without both checksum-verified assets")
    result = readback(lambda: gh("api", "--method", "PATCH", api, "-F", "draft=false"),
                      latest, completed, ready)
    print(result["html_url"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
