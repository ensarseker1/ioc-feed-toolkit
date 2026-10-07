import unittest

from ioc_feed_toolkit.readers import InputReadError, detect_format, parse_csv, parse_json, parse_text


class ReaderTests(unittest.TestCase):
    def test_text_ignores_blank_lines_and_comments(self):
        records = parse_text("# synthetic\n\nexample.test\n203.0.113.8\n", "fixture")
        self.assertEqual(2, len(records))
        self.assertEqual("line 3", records[0].location)

    def test_csv_recognizes_alias_columns_and_row_source(self):
        records = parse_csv(
            "ioc,ioc_type,provider\nExample.TEST,domain,feed-a\n203.0.113.9,ipv4,\n",
            "fallback",
        )
        self.assertEqual("feed-a", records[0].source)
        self.assertEqual("fallback", records[1].source)
        self.assertEqual("row 2", records[0].location)

    def test_csv_requires_indicator_column(self):
        with self.assertRaisesRegex(InputReadError, "must include"):
            parse_csv("thing,type\nexample.test,domain\n", "fixture")

    def test_csv_rejects_ambiguous_indicator_columns(self):
        with self.assertRaisesRegex(InputReadError, "multiple indicator columns"):
            parse_csv("indicator,value\nexample.test,other.test\n", "fixture")

    def test_csv_rejects_extra_fields(self):
        with self.assertRaisesRegex(InputReadError, "more fields"):
            parse_csv("indicator,type\nexample.test,domain,unexpected\n", "fixture")

    def test_json_accepts_envelope_and_per_record_metadata(self):
        records = parse_json(
            '{"source":"feed-a","indicators":['
            '{"value":"example.test","type":"domain"},'
            '{"indicator":"203.0.113.10","source":"feed-b"}]}'
            ,
            "fallback",
        )
        self.assertEqual(2, len(records))
        self.assertEqual("feed-a", records[0].source)
        self.assertEqual("feed-b", records[1].source)
        self.assertEqual("$.indicators[1]", records[1].location)

    def test_json_non_string_entries_are_returned_for_diagnostics(self):
        records = parse_json("[null, 42]", "fixture")
        self.assertIsNone(records[0].value)
        self.assertEqual(42, records[1].value)

    def test_invalid_json_reports_location(self):
        with self.assertRaisesRegex(InputReadError, "line 1, column"):
            parse_json("[}", "fixture")

    def test_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(InputReadError, "duplicate key"):
            parse_json('{"indicator":"one.test","indicator":"two.test"}', "fixture")

    def test_json_rejects_nonstandard_numeric_constants(self):
        with self.assertRaisesRegex(InputReadError, "numeric constant"):
            parse_json("[NaN]", "fixture")

    def test_format_detection_prefers_extension(self):
        self.assertEqual("json", detect_format("feed.json", "not json yet"))

    def test_format_detection_uses_content_for_stdin(self):
        self.assertEqual("csv", detect_format("-", "indicator,type\na.test,domain\n"))
        self.assertEqual("json", detect_format("-", " [\"a.test\"]"))
        self.assertEqual("text", detect_format("-", "a.test\n"))


if __name__ == "__main__":
    unittest.main()
