import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from ioc_feed_toolkit.cli import run


class CliTests(unittest.TestCase):
    def test_cli_combines_inputs_and_writes_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_path = root / "feed.txt"
            json_path = root / "feed.json"
            output_path = root / "result.json"
            text_path.write_text("Example.TEST\n203.0.113.11\n", encoding="utf-8")
            json_path.write_text(
                json.dumps([{"value": "example.test.", "type": "domain"}]),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = run([str(text_path), str(json_path), "-o", str(output_path)])
            result = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(0, exit_code)
            self.assertEqual(2, result["summary"]["unique_indicators"])
            self.assertEqual(1, result["summary"]["duplicate_observations"])
            self.assertIn("2 unique indicators", stderr.getvalue())

    def test_fail_on_reject_returns_one_but_still_writes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "feed.txt"
            output_path = root / "result.json"
            input_path.write_text("not valid\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = run(
                    [str(input_path), "--fail-on-reject", "--quiet", "-o", str(output_path)]
                )
            self.assertEqual(1, exit_code)
            self.assertEqual(1, json.loads(output_path.read_text())["summary"]["rejected"])

    def test_structural_input_error_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("[}", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = run([str(path), "--quiet"])
            self.assertEqual(2, exit_code)
            self.assertIn("invalid JSON", stderr.getvalue())

    def test_record_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.txt"
            path.write_text("one.test\ntwo.test\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = run([str(path), "--max-records", "1", "--quiet"])
            self.assertEqual(2, exit_code)

    def test_byte_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.txt"
            path.write_text("example.test\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = run([str(path), "--max-bytes", "2", "--quiet"])
            self.assertEqual(2, exit_code)


if __name__ == "__main__":
    unittest.main()
