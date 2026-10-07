import json
import unittest

from ioc_feed_toolkit.output import render_csv, render_json
from ioc_feed_toolkit.pipeline import FeedProcessor, InputRecord


class PipelineTests(unittest.TestCase):
    def test_deduplication_preserves_all_distinct_provenance(self):
        processor = FeedProcessor()
        processor.add(InputRecord("Example.TEST", "feed-b", "line 2"))
        processor.add(InputRecord("example.test.", "feed-a", "row 3", "domain"))
        result = processor.result()

        self.assertEqual(1, len(result.indicators))
        self.assertEqual("example.test", result.indicators[0].value)
        self.assertEqual(["feed-a", "feed-b"], [p.source for p in result.indicators[0].provenance])
        self.assertEqual(1, result.duplicate_observations)

    def test_exact_duplicate_observation_is_counted(self):
        processor = FeedProcessor()
        record = InputRecord("example.test", "same", "line 1")
        processor.add(record)
        processor.add(record)
        result = processor.result()
        self.assertEqual(2, result.observations)
        self.assertEqual(1, result.duplicate_observations)
        self.assertEqual(1, len(result.indicators[0].provenance))

    def test_rejection_has_actionable_context(self):
        processor = FeedProcessor()
        processor.add(InputRecord("not a.domain", "synthetic", "line 7", "domain"))
        rejected = processor.result().rejected[0]
        self.assertEqual("synthetic", rejected.source)
        self.assertEqual("line 7", rejected.location)
        self.assertEqual("domain", rejected.declared_type)
        self.assertIn("invalid label", rejected.reason)

    def test_non_string_json_value_is_rejected_safely(self):
        processor = FeedProcessor()
        processor.add(InputRecord({"nested": True}, "synthetic", "$[0]"))
        rejected = processor.result().rejected[0]
        self.assertEqual('{"nested":true}', rejected.input)
        self.assertEqual("indicator must be a string", rejected.reason)

    def test_result_order_is_independent_of_input_order(self):
        records = [
            InputRecord("203.0.113.7", "z", "line 2"),
            InputRecord("example.test", "a", "line 1"),
            InputRecord("bad value", "m", "line 3"),
        ]
        first = FeedProcessor()
        first.add_many(records)
        second = FeedProcessor()
        second.add_many(reversed(records))
        self.assertEqual(render_json(first.result()), render_json(second.result()))

    def test_json_output_contains_summary(self):
        processor = FeedProcessor()
        processor.add(InputRecord("203.0.113.7", "synthetic", "line 1"))
        output = json.loads(render_json(processor.result()))
        self.assertEqual(1, output["summary"]["unique_indicators"])
        self.assertEqual("ipv4", output["indicators"][0]["type"])

    def test_csv_output_includes_accepts_and_rejects(self):
        processor = FeedProcessor()
        processor.add(InputRecord("example.test", "feed", "line 1"))
        processor.add(InputRecord("bad value", "feed", "line 2"))
        output = render_csv(processor.result())
        self.assertIn("accepted,domain,example.test", output)
        self.assertIn("rejected", output)
        self.assertIn("could not infer IOC type", output)

    def test_csv_formula_prefix_is_neutralized(self):
        processor = FeedProcessor()
        processor.add(InputRecord("bad value", "=CMD()", "line 1"))
        output = render_csv(processor.result())
        self.assertIn("'=CMD()", output)


if __name__ == "__main__":
    unittest.main()
