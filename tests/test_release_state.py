import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sync import release_state as rs

BASE, COMMIT, TREE = "a" * 40, "b" * 40, "c" * 40
TAG = "psh-7.25.6-aaaaaaaaaaaa-bbbbbbbbbbbb"
M = rs.manifest(TAG, BASE, COMMIT, TREE, 123, rs.digest(b"fixture ZIP"))


def release(*names, published=False):
    return dict(id=456, draft=not published, prerelease=True, tag_name=TAG, html_url="https://example.test",
                body=rs.PREFIX + json.dumps(M) + " -->",
                assets=[dict(name=n, digest=M["zip" if n == rs.ZIP else "sums"], state="uploaded") for n in names])


class ReleaseTest(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(rs.route(None, TAG, BASE), ("build", None))
        self.assertEqual(rs.route(release(rs.ZIP, rs.SUM, published=True), TAG, BASE), ("published", None))
        self.assertEqual(rs.route(release(rs.ZIP, rs.SUM), TAG, BASE), ("resume", M))
        self.assertEqual(rs.route(release(rs.SUM), TAG, BASE), ("resume-files", M))

    def test_invalid_existing_assets_fail_closed(self):
        cases = [release(rs.ZIP, published=True), release("unexpected"), release(rs.ZIP, rs.ZIP)]
        wrong = release(rs.ZIP)
        wrong["assets"][0]["digest"] = rs.digest(b"other")
        starter = release(rs.ZIP)
        starter["assets"][0]["state"] = "starter"
        cases.extend((wrong, starter, dict(release(rs.ZIP), body="old draft")))
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                rs.route(case, TAG, BASE)

    def test_dispatch_is_signal_only(self):
        self.assertTrue(rs.dispatch_allowed({"action": "upstream-stable-release",
            "client_payload": {"repository": "2dust/v2rayN", "tag": "not trusted"}}))
        self.assertFalse(rs.dispatch_allowed({"action": "upstream-stable-release",
            "client_payload": {"repository": "someone/other"}}))
        self.assertFalse(rs.dispatch_allowed({"action": "push"}))

    def test_uncertain_creation_reads_back_before_retry(self):
        states = iter([None, release(rs.ZIP, rs.SUM)])
        calls = []
        def bad_response():
            calls.append("create")
            raise subprocess.CalledProcessError(1, "gh")
        self.assertEqual(rs.readback(bad_response, lambda: next(states), bool, lambda _: None)["id"], 456)
        self.assertEqual(calls, ["create"])

    def test_publish_complete_draft_has_no_upload_or_local_artifact(self):
        r = release(rs.ZIP, rs.SUM)
        calls = []
        def fake_gh(*args):
            calls.append(args)
            if args[:3] == ("api", "--method", "PATCH"):
                r["draft"] = False
                raise subprocess.CalledProcessError(1, "gh")
            return json.dumps(r)
        with patch.object(rs, "gh", fake_gh), patch.object(rs, "lookup", return_value=r), \
                patch.dict(os.environ, {"GITHUB_REPOSITORY": rs.REPO, "GITHUB_REF": "refs/heads/main"}), \
                patch("sys.argv", ["release_state.py", "publish", TAG, BASE, COMMIT, TREE, "123"]):
            rs.main()
        self.assertEqual(sum(c[:3] == ("api", "--method", "PATCH") for c in calls), 1)
        self.assertFalse(any(c[0] == "release" for c in calls))

    def test_partial_draft_reuses_original_and_preserves_uploaded_file(self):
        r = release(rs.ZIP)
        calls = []
        def fake_gh(*args):
            calls.append(args)
            if args[:2] == ("release", "upload"):
                self.assertTrue(args[3].endswith(rs.SUM))
                self.assertEqual(Path(args[3]).read_bytes(), rs.checksum_line(M["zip"]))
                r["assets"].append(release(rs.SUM)["assets"][0])
                raise subprocess.CalledProcessError(1, "gh")
            if args[:3] == ("api", "--method", "PATCH"):
                r["draft"] = False
            return json.dumps(r)
        with tempfile.TemporaryDirectory() as folder, patch.object(rs, "gh", fake_gh), \
                patch.object(rs, "lookup", return_value=r), \
                patch.dict(os.environ, {"GITHUB_REPOSITORY": rs.REPO, "GITHUB_REF": "refs/heads/main"}), \
                patch("sys.argv", ["release_state.py", "publish", TAG, BASE, COMMIT, TREE, "123"]):
            actual = Path(folder)
            with patch.object(rs, "Path", lambda _: actual):
                (actual / rs.ZIP).write_bytes(b"not the original")
                with self.assertRaisesRegex(ValueError, "differs"):
                    rs.main()
                self.assertEqual(calls, [])
                (actual / rs.ZIP).write_bytes(b"fixture ZIP")
                rs.main()
        self.assertEqual(sum(c[:2] == ("release", "upload") for c in calls), 1)
        self.assertFalse(any("--clobber" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
