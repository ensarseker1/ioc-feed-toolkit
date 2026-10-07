import unittest

from ioc_feed_toolkit.normalize import IndicatorValidationError, normalize_indicator


class NormalizeTests(unittest.TestCase):
    def test_ipv4_is_canonical(self):
        self.assertEqual(("ipv4", "192.0.2.10"), normalize_indicator(" 192.0.2.10 "))

    def test_ipv6_is_compressed_and_lowercase(self):
        self.assertEqual(
            ("ipv6", "2001:db8::1"),
            normalize_indicator("2001:0DB8:0000:0000:0000:0000:0000:0001"),
        )

    def test_ip_prefix_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "prefixes"):
            normalize_indicator("192.0.2.0/24", "ip")

    def test_scoped_ipv6_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "scoped"):
            normalize_indicator("fe80::1%en0", "ipv6")

    def test_declared_ip_version_is_enforced(self):
        with self.assertRaisesRegex(IndicatorValidationError, "expected IPv4"):
            normalize_indicator("2001:db8::1", "ipv4")

    def test_domain_is_lowercase_and_trailing_dot_removed(self):
        self.assertEqual(("domain", "example.test"), normalize_indicator("Example.TEST."))

    def test_unicode_domain_is_idna_encoded(self):
        self.assertEqual(("domain", "xn--bcher-kva.example"), normalize_indicator("bücher.example"))

    def test_single_label_domain_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "at least one dot"):
            normalize_indicator("localhost", "domain")

    def test_invalid_domain_label_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "invalid label"):
            normalize_indicator("bad_label.example", "domain")

    def test_invalid_numeric_ip_is_not_accepted_as_domain(self):
        with self.assertRaisesRegex(IndicatorValidationError, "invalid IP"):
            normalize_indicator("999.999.999.999")

    def test_hash_algorithm_is_inferred_and_lowercased(self):
        value = "A" * 64
        self.assertEqual(("hash-sha256", "a" * 64), normalize_indicator(value))

    def test_explicit_hash_algorithm_is_enforced(self):
        with self.assertRaisesRegex(IndicatorValidationError, "expected hash-sha256"):
            normalize_indicator("a" * 32, "sha256")

    def test_non_hex_hash_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "hexadecimal"):
            normalize_indicator("z" * 32, "md5")

    def test_url_normalizes_scheme_host_port_percent_and_fragment(self):
        self.assertEqual(
            ("url", "https://example.test/a%2Fpath?q=%AA"),
            normalize_indicator("HTTPS://Example.TEST:443/a%2fpath?q=%aa#fragment", "url"),
        )

    def test_url_adds_root_path(self):
        self.assertEqual(("url", "http://example.test/"), normalize_indicator("http://example.test"))

    def test_url_normalizes_ipv6_host(self):
        self.assertEqual(
            ("url", "http://[2001:db8::1]/"),
            normalize_indicator("http://[2001:0db8:0:0:0:0:0:1]:80/"),
        )

    def test_url_userinfo_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "userinfo"):
            normalize_indicator("https://user:secret@example.test/", "url")

    def test_url_bad_percent_escape_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "percent escape"):
            normalize_indicator("https://example.test/%zz", "url")

    def test_url_whitespace_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "whitespace"):
            normalize_indicator("https://example.test/a path", "url")

    def test_non_string_declared_type_has_validation_error(self):
        with self.assertRaisesRegex(IndicatorValidationError, "declared type must be a string"):
            normalize_indicator("example.test", 3)  # type: ignore[arg-type]

    def test_defanged_value_is_not_refanged(self):
        with self.assertRaises(IndicatorValidationError):
            normalize_indicator("example[.]test")

    def test_unsupported_type_is_rejected(self):
        with self.assertRaisesRegex(IndicatorValidationError, "unsupported declared type"):
            normalize_indicator("example.test", "email")


if __name__ == "__main__":
    unittest.main()
