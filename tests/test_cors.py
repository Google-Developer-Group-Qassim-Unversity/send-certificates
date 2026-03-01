import re
import unittest

from app.main import ALLOWED_ORIGINS, build_origin_regex


class TestBuildOriginRegex(unittest.TestCase):
    def setUp(self):
        self.pattern = build_origin_regex(ALLOWED_ORIGINS)
        self.regex = re.compile(self.pattern)

    def assert_matches(self, origin: str):
        self.assertTrue(
            self.regex.fullmatch(origin),
            f"'{origin}' should match pattern but didn't",
        )

    def assert_no_match(self, origin: str):
        self.assertFalse(
            self.regex.fullmatch(origin),
            f"'{origin}' should NOT match pattern but did",
        )

    def test_exact_domain_gdg_q(self):
        self.assert_matches("https://gdg-q.com")

    def test_subdomain_gdg_q(self):
        self.assert_matches("https://www.gdg-q.com")
        self.assert_matches("https://api.gdg-q.com")
        self.assert_matches("https://sub.sub.gdg-q.com")
        self.assert_matches("https://admin.gdg-q.com")

    def test_vercel_app(self):
        self.assert_matches("https://myapp.vercel.app")
        self.assert_matches("https://some-project.vercel.app")
        self.assert_matches("https://a-b-c-123.vercel.app")

    def test_vercel_app_real_world(self):
        self.assert_matches(
            "https://score-leaderboard-admin-app-git-main-albrrak773s-projects.vercel.app"
        )
        self.assert_matches(
            "https://score-leaderboard-admin-4yvt4xrsq-albrrak773s-projects.vercel.app"
        )
        self.assert_matches("https://score-leaderboard-admin-app-ten.vercel.app")
        self.assert_matches(
            "https://score-leaderboard-admin-app-albrrak773s-projects.vercel.app"
        )

    def test_exact_domain_albrrak773(self):
        self.assert_matches("https://albrrak773.com")

    def test_subdomain_albrrak773(self):
        self.assert_matches("https://www.albrrak773.com")
        self.assert_matches("https://api.albrrak773.com")
        self.assert_matches("https://sub.sub.albrrak773.com")
        self.assert_matches("https://refactor.albrrak773.com")

    def test_localhost_with_port(self):
        self.assert_matches("http://localhost:3000")
        self.assert_matches("http://localhost:5173")
        self.assert_matches("http://localhost:8000")
        self.assert_matches("http://localhost:8080")

    def test_localhost_without_port(self):
        self.assert_matches("http://localhost")

    def test_127_0_0_1_with_port(self):
        self.assert_matches("http://127.0.0.1:3000")
        self.assert_matches("http://127.0.0.1:5173")
        self.assert_matches("http://127.0.0.1:8000")

    def test_127_0_0_1_without_port(self):
        self.assert_matches("http://127.0.0.1")

    def test_reject_http_gdg_q(self):
        self.assert_no_match("http://gdg-q.com")

    def test_reject_http_vercel_app(self):
        self.assert_no_match("http://myapp.vercel.app")

    def test_reject_http_albrrak773(self):
        self.assert_no_match("http://albrrak773.com")

    def test_reject_unknown_domain(self):
        self.assert_no_match("https://evil.com")
        self.assert_no_match("https://malicious.com")

    def test_reject_wrong_protocol(self):
        self.assert_no_match("ftp://gdg-q.com")
        self.assert_no_match("ws://localhost:3000")

    def test_empty_origins(self):
        pattern = build_origin_regex([])
        self.assertEqual(pattern, "")

    def test_single_origin_no_wildcard(self):
        pattern = build_origin_regex(["https://example.com"])
        regex = re.compile(pattern)
        self.assertTrue(regex.fullmatch("https://example.com"))
        self.assertFalse(regex.fullmatch("https://sub.example.com"))


if __name__ == "__main__":
    unittest.main()
