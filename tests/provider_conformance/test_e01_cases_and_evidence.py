"""Logic-only tests for the case suite, evidence capture and the manifest.

These run the full 15-case suite against the in-memory fake. That proves the
SUITE is wired correctly and that its verdicts are computed honestly. It does
NOT prove provider semantics (E07-M1), and one of the tests below asserts that
the suite says so itself.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests.provider_conformance.cases import (FAIL, PASS, UNPROVEN, CaseContext,
                                              run_all)
from tests.provider_conformance.e01_s3_harness import main
from tests.provider_conformance.evidence import (MANIFEST_FILENAME,
                                                 EvidenceRecorder,
                                                 compute_manifest,
                                                 verify_manifest)
from tests.provider_conformance.memory_store import MemoryObjectStore


def run_suite(tmpdir, store=None, ordinary_store=None):
    store = store or MemoryObjectStore()
    recorder = EvidenceRecorder(run_dir=tmpdir, run_id="run-test",
                                provider_id=store.PROVIDER_ID,
                                can_prove_provider_semantics=bool(
                                    store.CAN_PROVE_PROVIDER_SEMANTICS))
    ctx = CaseContext(store=store, prefix="unit-suite", run_id="run-test",
                      recorder=recorder, ordinary_store=ordinary_store,
                      ordinary_principal_label="ordinary" if ordinary_store else "")
    return {r.case_id: r for r in run_all(ctx)}, recorder


class SuiteCoverage(unittest.TestCase):
    def test_all_fifteen_commission_cases_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir)
        self.assertEqual(sorted(results), [f"c{i:02d}" for i in range(1, 16)])

    def test_writer_logic_cases_pass_against_a_well_behaved_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir)
        for case_id, result in sorted(results.items()):
            if case_id == "c13":
                continue                       # needs a second principal
            self.assertEqual(result.status, PASS,
                             f"{case_id} {result.title}: {result.detail}")

    def test_c13_is_unproven_without_a_second_principal(self):
        """The important one: an unprovable control must never read as PASS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir)
        self.assertEqual(results["c13"].status, UNPROVEN)
        self.assertIn("provider-side permission denial", results["c13"].detail)

    def test_c13_passes_only_on_a_real_permission_denial(self):
        store = MemoryObjectStore()
        ordinary = MemoryObjectStore()
        ordinary._objects = store._objects
        ordinary._versions = store._versions
        ordinary._head_write_denied = True
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir, store=store, ordinary_store=ordinary)
        self.assertEqual(results["c13"].status, PASS, results["c13"].detail)

    def test_c13_fails_when_an_ordinary_caller_can_write_head(self):
        store = MemoryObjectStore()
        ordinary = MemoryObjectStore()
        ordinary._objects = store._objects
        ordinary._versions = store._versions          # no denial configured
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir, store=store, ordinary_store=ordinary)
        self.assertEqual(results["c13"].status, FAIL)
        self.assertIn("ORDINARY_PRINCIPAL_WROTE_AUTHORITATIVE_HEAD",
                      results["c13"].detail)

    def test_c05_records_that_the_bypass_path_accepts_an_old_epoch(self):
        """Reproduces the Sydney CRITICAL: raw CAS with the current ETag takes
        an old-epoch body, which is why the writer must gate it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir)
        self.assertEqual(results["c05"].status, PASS)
        self.assertTrue(results["c05"].facts["provider_accepted_rollback_via_bypass"])

    def test_a_case_crash_is_reported_as_fail_not_skipped(self):
        class Exploding(MemoryObjectStore):
            def read_after_write_probe(self, key, data):
                raise RuntimeError("boom")
        with tempfile.TemporaryDirectory() as tmpdir:
            results, _ = run_suite(tmpdir, store=Exploding())
        self.assertEqual(results["c01"].status, FAIL)
        self.assertIn("UNHANDLED_EXCEPTION", results["c01"].detail)


class EvidenceAndManifest(unittest.TestCase):
    def test_evidence_records_carry_the_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results, recorder = run_suite(tmpdir)
            self.assertEqual(results["c14"].status, PASS, results["c14"].detail)
            for record in recorder.records:
                for field in ("run_id", "seq", "ts_utc", "ts_ns", "provider_id",
                              "case_id", "operation", "outcome",
                              "request_metadata", "response_metadata"):
                    self.assertIn(field, record)
            files = os.listdir(os.path.join(tmpdir, "records"))
            self.assertTrue(files)

    def test_credentials_are_never_recorded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = EvidenceRecorder(run_dir=tmpdir, run_id="r", provider_id="p",
                                        can_prove_provider_semantics=False)
            entry = recorder.record(
                case_id="c00", operation="op", outcome=PASS,
                request_metadata={"authorization": "AWS4-HMAC-SHA256 SECRET",
                                  "x-amz-security-token": "TOKEN",
                                  "if_match": '"etag"'},
                response_metadata={"etag": '"etag"', "secret_access_key": "AKIA"})
        self.assertEqual(entry["request_metadata"], {"if_match": '"etag"'})
        self.assertEqual(entry["response_metadata"], {"etag": '"etag"'})

    def test_manifest_is_deterministic_and_change_sensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, recorder = run_suite(tmpdir)
            first = compute_manifest(tmpdir)
            second = compute_manifest(tmpdir)
            self.assertEqual(first["evidence_digest"], second["evidence_digest"])
            recorder.finalise()
            report = verify_manifest(tmpdir)
            self.assertTrue(report["match"])
            # One changed byte anywhere in the evidence changes the digest.
            victim = os.path.join(tmpdir, "records",
                                  sorted(os.listdir(os.path.join(tmpdir, "records")))[0])
            with open(victim, "ab") as handle:
                handle.write(b" ")
            tampered = verify_manifest(tmpdir)
            self.assertFalse(tampered["match"])

    def test_manifest_excludes_itself_and_covers_every_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, recorder = run_suite(tmpdir)
            recorder.write_summary({"k": "v"})
            manifest = recorder.finalise()
            listed = {entry["path"] for entry in manifest["files"]}
            self.assertNotIn(MANIFEST_FILENAME, listed)
            on_disk = set()
            for root, _dirs, names in os.walk(tmpdir):
                for name in names:
                    if name == MANIFEST_FILENAME:
                        continue
                    rel = os.path.relpath(os.path.join(root, name), tmpdir)
                    on_disk.add(rel.replace(os.sep, "/"))
            self.assertEqual(listed, on_disk)


class RunnerVerdict(unittest.TestCase):
    def test_selftest_run_is_labelled_not_provider_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code = main(["selftest", "--evidence-dir", tmpdir])
            with open(os.path.join(tmpdir, "run_summary.json"), "rb") as handle:
                summary = json.loads(handle.read().decode("utf-8"))
        verdict = summary["verdict"]
        self.assertFalse(verdict["is_provider_evidence"])
        self.assertFalse(verdict["can_prove_provider_semantics"])
        self.assertEqual(verdict["PROVIDER_ACCEPTED"], "NO")
        # c13 is UNPROVEN on a fake, so the run is INCOMPLETE, not PASS.
        self.assertEqual(verdict["technical_verdict"], "TECHNICAL_INCOMPLETE")
        self.assertEqual(code, 1)

    def test_live_run_refuses_without_isolation_acknowledgement(self):
        self.assertEqual(main(["live", "--bucket", "b", "--region", "r",
                               "--prefix", "e01/x", "--evidence-dir", "d"]), 2)

    def test_live_run_refuses_a_prefix_outside_the_e01_namespace(self):
        self.assertEqual(main(["live", "--bucket", "b", "--region", "r",
                               "--prefix", "production/stage-a",
                               "--evidence-dir", "d",
                               "--ack-isolated-test-only"]), 2)

    def test_verify_manifest_command_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main(["selftest", "--evidence-dir", tmpdir])
            self.assertEqual(main(["verify-manifest", tmpdir]), 0)


class NonProductionBoundary(unittest.TestCase):
    def test_harness_creates_no_stage_a_runtime_tree(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        self.assertFalse(os.path.exists(os.path.join(root, "stage_a")))

    def test_harness_does_not_import_stage_a_or_production_packages(self):
        """Import-statement scan. Only real import LINES count, so this test's
        own assertion strings cannot satisfy or trip it."""
        import pathlib
        import re
        pattern = re.compile(
            r"^\s*(?:from|import)\s+(stage_a|tracker_identity|population)",
            re.MULTILINE)
        scanned = 0
        for path in sorted(pathlib.Path(__file__).parent.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            scanned += 1
            hits = pattern.findall(path.read_text(encoding="utf-8"))
            self.assertEqual(hits, [], f"{path.name} imports {hits}")
        self.assertGreaterEqual(scanned, 8)   # the scan is live, not vacuous

    def test_fake_store_can_never_claim_provider_proof(self):
        self.assertFalse(MemoryObjectStore.CAN_PROVE_PROVIDER_SEMANTICS)


if __name__ == "__main__":
    unittest.main()
