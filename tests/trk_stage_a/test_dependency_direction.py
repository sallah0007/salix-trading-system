import ast, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def imports(pkg):
    out = set()
    for dp, _, fs in os.walk(os.path.join(ROOT, pkg)):
        for f in fs:
            if f.endswith(".py"):
                with open(os.path.join(dp, f)) as fh:
                    for n in ast.walk(ast.parse(fh.read())):
                        if isinstance(n, ast.Import):
                            out.update(a.name.split(".")[0] for a in n.names)
                        elif isinstance(n, ast.ImportFrom) and n.level == 0:
                            out.add((n.module or "").split(".")[0])
    return out

class DependencyDirection(unittest.TestCase):
    def test_baseline_and_component_layers_never_import_stage_a(self):
        for pkg in ("tracker_identity", "tracker_component"):
            self.assertNotIn("stage_a", imports(pkg), pkg)
    def test_stage_a_depends_only_on_tracker_layers_and_stdlib(self):
        allowed_third = {"tracker_identity", "tracker_component", "stage_a"}
        import sys
        for m in imports("stage_a"):
            if m and m not in allowed_third:
                self.assertIn(m, sys.stdlib_module_names, "non-stdlib dependency %s" % m)
    def test_stage_a_does_not_reference_salix_ai_or_engine(self):
        for dp, _, fs in os.walk(os.path.join(ROOT, "stage_a")):
            for f in fs:
                if f.endswith(".py"):
                    with open(os.path.join(dp, f)) as fh:
                        t = fh.read().lower()
                    for bad in ("salix_ai", "salix-ai", "gateway_client", "requests", "urllib"):
                        self.assertNotIn(bad, t, "%s mentions %s" % (f, bad))

if __name__ == "__main__":
    unittest.main()
