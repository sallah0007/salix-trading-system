"""R36: Composer 27/28 BUILD_OUTPUT_PACKAGE seven-field producer-binding admission through the REAL intake route (admit + TrackerPipeline.run + the Core/ClaimService order path). The authority lookup is SUPPLIED by the test (source-owned in reality); nothing is appointed."""
import copy, hashlib, unittest
from stage_a.binding.producer_binding import SEVEN_FIELDS
from stage_a.tracker.quant_intake_adapter import admit, QUANT_FEATURE, FAILED_REQUESTED_BUILD
from stage_a.tracker.pipeline import TrackerPipeline
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF
from .test_r29_intake_order import issue, br
IFACE = "COMPOSER_BUILD_OUTPUT_PACKAGE"
def rec(**o):
    d = {"scope": "SALIX_STAGE_A", "interface_id": IFACE, "version": "v9", "content_hash": hashlib.sha256(b"x").hexdigest(), "source_authority": "AUTH-1", "acceptance_record": "ACC-1", "validity/supersession": "CURRENT"}; d.update(o); return d
def AUTH():
    reg = {(r["scope"], r["interface_id"], r["version"]): r for r in (rec(), rec(interface_id="FW_BINDING"))}          # a DIFFERENT interface's binding is ALSO admitted by the register
    return {"lookup": lambda s, i, v: reg.get((s, i, v)), "source_ref": "SUPPLIED-REGISTER", "interface_id": IFACE}
def run(pkg, auth):
    rig = Rig(); p = pkg; sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key; issue(rig.claims, subject_key=sk); abs_(rig.claims, OA.order_id_for("cand-1"), br())
    rig.pipe = TrackerPipeline(store=rig.store, claims=rig.claims, journals=rig.journals, clock=rig.pipe._clock, events=rig.events, accepted_fit_generations=rig.fits, conformance_source=lambda p: SIM_CONF, duty_source=rig.pipe._duty_source, simulation=True, producer_authority=auth); return rig, rig.pipe.run(p)
class Route(unittest.TestCase):
    def pkg(self, **o): return package(order_id=OA.order_id_for("cand-1"), **o)
    def test_admitted_binding_passes_the_real_route_and_every_unsatisfied_variant_fails_the_build_before_acceptance(self):
        rig, out = run(self.pkg(producer_binding=rec()), AUTH()); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED"); self.assertNotIn("COMPOSER_PRODUCER_BINDING_ADMISSION", [d for d, _ in out.limits])
        bad = {"missing": None, "foreign_interface": rec(interface_id="FW_BINDING"), "field_mismatch": rec(**{"validity/supersession": "SUPERSEDED"}), "unknown_key": rec(version="v0"), "empty_field": rec(acceptance_record=""), "short_hash": rec(content_hash="abc"), "extra_field": dict(rec(), z="1")}
        for name, b in bad.items():
            rig, out = run(self.pkg(producer_binding=copy.deepcopy(b)), AUTH()); self.assertFalse(getattr(out, "accepted", None) is not None and out.accepted.kind == "CANONICAL_ACCEPTED", name); self.assertEqual(out.admission.classification, FAILED_REQUESTED_BUILD, name)
            self.assertTrue(any(d == "PRODUCER_BINDING" for d, _ in out.admission.failed), name)
        rig, out = run(self.pkg(producer_binding=rec(interface_id="FW_BINDING")), AUTH()); self.assertIn(("PRODUCER_BINDING", "PRODUCER_BINDING_FOREIGN_INTERFACE"), out.admission.failed)         # admitted elsewhere, still not THIS interface
    def test_without_a_supplied_authority_the_duty_is_labelled_unverified_not_invented_and_the_build_is_not_failed_for_an_unreadable_source(self):
        a = admit(self.pkg(), accepted_fit_generations={}, conformance=SIM_CONF); self.assertEqual(a.classification, QUANT_FEATURE); self.assertIn(("COMPOSER_PRODUCER_BINDING_ADMISSION", "NOT_VERIFIED_NO_AUTHORITY_SUPPLIED"), a.unverified)
        self.assertEqual([c for c in a.failed if c[0] == "PRODUCER_BINDING"], [])
    def test_the_binding_is_part_of_the_package_content_hash_and_a_malformed_authority_holds(self):
        p1, p2 = self.pkg(producer_binding=rec()), self.pkg(producer_binding=rec(source_authority="AUTH-2")); self.assertNotEqual(p1.content_hash(), p2.content_hash()); self.assertEqual(self.pkg().content_hash(), self.pkg().content_hash())
        a = admit(p1, accepted_fit_generations={}, conformance=SIM_CONF, producer_authority={"lookup": None}); self.assertIn(("PRODUCER_BINDING", "PRODUCER_AUTHORITY_MALFORMED"), a.failed)
if __name__ == "__main__": unittest.main()
