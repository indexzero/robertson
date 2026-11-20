"""Isolated tests against throwaway git repositories. No gh, no network."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("pr_sizes", Path(__file__).parents[1] / "scripts/pr-sizes.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)

CONFIG = {
    "rules": [
        {"group": "docs", "patterns": ["README.md", "doc/**"]},
        {"group": "generated", "patterns": ["test/vectors.json", "package.json"]},
        {"group": "code", "patterns": ["index.js", "lib/**"]},
        {"group": "tests", "patterns": ["test/*.js"]},
    ],
    "comment_prefixes": [{"patterns": ["**/*.js"], "prefixes": ["//"]}],
    "test_call_regex": r"(^|[^.A-Za-z_])test\(",
}

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class Stack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.repo = self.dir / "repo"
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.dir)
        self.config = self.dir / "config.json"
        self.config.write_text(json.dumps(CONFIG))
        self.write({"README.md": "# x\n", "index.js": "module.exports = 1\n",
                    "test/a.js": "test('one', () => {})\n"})
        self.base = self.commit("base")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=ENV, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, files):
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def measure(self, *items, base=None):
        out = self.dir / "out.json"
        code = p.main(["--repo", str(self.repo), "--base", base or self.base, "--config", str(self.config),
                       "--out", str(self.dir / "out.md"), "--json", str(out), *items])
        return code, json.loads(out.read_text())

    def test_counts_by_group(self):
        self.write({"lib/a.js": "// a comment\n\nconst a = 1 // trailing\n",
                    "README.md": "# x\none two three\n\n",
                    "test/a.js": "test('one', () => {})\n\ntest('two', () => {})\n",
                    "test/vectors.json": "[]\n", "other.txt": "x\n"})
        first = self.commit("first")
        self.write({"lib/a.js": "// a comment\n\nconst a = 2 // trailing\n"})
        second = self.commit("second")
        code, data = self.measure("ref:" + first, second)
        self.assertEqual(code, 0)
        one = data["steps"][0]["groups"]
        self.assertEqual((one["code"]["added"], one["code"]["substantive"]), (3, 1))
        self.assertEqual((one["docs"]["added"], one["docs"]["removed"], one["docs"]["substantive"]), (2, 0, 1))
        self.assertEqual((one["tests"]["added"], one["tests"]["substantive"], one["tests"]["tests_added"]), (2, 1, 1))
        self.assertEqual(one["generated"]["added"], 1)
        self.assertEqual(one["unassigned"]["files"], 1)
        self.assertEqual(data["steps"][0]["doc_words"], {"added": 3, "removed": 0})
        # the second step rewrites a line the first added: counted twice in the sum, once in the stack
        self.assertEqual(data["sum"]["groups"]["code"]["added"], 4)
        self.assertEqual(data["total"]["groups"]["code"]["added"], 3)
        self.assertEqual(data["tests_in_tree"], {self.base: 1, first: 2, second: 2})
        self.assertEqual(data["flags"], [])
        self.assertNotIn("test_runs", data)
        self.assertIn("`other.txt`", (self.dir / "out.md").read_text())

    def test_flags_what_breaks_the_assumptions(self):
        self.write({"lib/a.js": "1\n"})
        self.commit("one")
        self.write({"lib/a.js": "2\n"})
        two = self.commit("two")
        self.git("checkout", "-q", "-b", "side", self.base)
        self.write({"lib/b.js": "3\n"})
        side = self.commit("side")
        self.git("mv", "lib/b.js", "lib/c.js")
        moved = self.commit("rename")
        _, data = self.measure(two, side, moved)
        self.assertTrue(any("2 commits" in f for f in data["flags"]))
        self.assertTrue(any("not an ancestor" in f for f in data["flags"]))
        self.assertEqual(data["stack"][2]["created_deleted_renamed"], ["R lib/b.js -> lib/c.js"])
        code = p.main(["--repo", str(self.repo), "--base", self.base, "--config", str(self.config),
                       "--out", os.devnull, "--strict", two])
        self.assertEqual(code, 2)

    def test_globs(self):
        self.assertTrue(p.glob_regex("doc/**").match("doc/a/b.md"))
        self.assertTrue(p.glob_regex("**/*.lock").match("Cargo.lock"))
        self.assertTrue(p.glob_regex("**/*.lock").match("a/b/yarn.lock"))
        self.assertFalse(p.glob_regex("test/*.js").match("test/helpers/a.js"))
        self.assertFalse(p.glob_regex("README.md").match("doc/README.md"))


if __name__ == "__main__":
    unittest.main()
