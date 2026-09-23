import json
import unittest
import urllib.error
import urllib.request

from focuscat import config
from focuscat import watcher as w
from focuscat.server import ReportServer


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.w = w.FocusWatcher(dict(config.DEFAULTS))
        self.srv = ReportServer(self.w, 0).start()

    def tearDown(self):
        self.srv.stop()

    def post(self, payload, headers=None):
        h = {"Content-Type": "application/json", "X-Focus-Cat": "1"}
        h.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.srv.port}/report",
                                     data=json.dumps(payload).encode(), headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=3) as res:
            return json.load(res)

    def test_report_is_stored(self):
        data = self.post({"url": "https://youtube.com/shorts/x", "tabId": 5, "focused": True})
        self.assertIsNone(data["close"])
        self.assertTrue(self.w.status()["connected"])
        self.assertEqual(self.w.status()["url"], "https://youtube.com/shorts/x")

    def test_extension_origin_allowed(self):
        self.post({"url": "x"}, {"Origin": "moz-extension://abc"})

    def test_web_pages_are_rejected(self):
        for headers in ({"X-Focus-Cat": "0"}, {"Origin": "https://evil.example"}):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.post({"url": "x"}, headers)
            self.assertEqual(ctx.exception.code, 403)

    def test_preflight_allowed_for_extensions_only(self):
        def preflight(origin):
            req = urllib.request.Request(f"http://127.0.0.1:{self.srv.port}/report", method="OPTIONS",
                                         headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                  "Access-Control-Request-Headers": "content-type,x-focus-cat"})
            return urllib.request.urlopen(req, timeout=3)

        with preflight("moz-extension://1234") as res:
            self.assertEqual(res.status, 204)
            self.assertEqual(res.headers["Access-Control-Allow-Origin"], "moz-extension://1234")
            self.assertIn("X-Focus-Cat", res.headers["Access-Control-Allow-Headers"])
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            preflight("https://evil.example")
        self.assertEqual(ctx.exception.code, 403)

    def test_report_response_carries_cors_header(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.srv.port}/report", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Focus-Cat": "1",
                                              "Origin": "moz-extension://1234"})
        with urllib.request.urlopen(req, timeout=3) as res:
            self.assertEqual(res.headers["Access-Control-Allow-Origin"], "moz-extension://1234")

    def test_second_instance_cannot_bind(self):
        with self.assertRaises(OSError):
            ReportServer(self.w, self.srv.port)


if __name__ == "__main__":
    unittest.main()
