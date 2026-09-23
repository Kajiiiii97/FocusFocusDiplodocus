import unittest

from focuscat import config
from focuscat import watcher as w

SHORTS = "https://www.youtube.com/shorts/abc123"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class WatcherTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cfg = dict(config.DEFAULTS, notice_after_seconds=10, close_after_seconds=60,
                        forgive_after_seconds=30, second_chance_seconds=15)
        self.w = w.FocusWatcher(self.cfg, clock=self.clock)
        self.w.tick()

    def run_for(self, seconds, url=SHORTS, focused=True, tab=7):
        close = None
        for _ in range(int(seconds * 2)):
            self.clock.now += 0.5
            got = self.w.report(url, tab, focused)
            close = close if got is None else got
            self.w.tick()
        return close

    def test_matching(self):
        pats = config.DEFAULTS["blocked"]
        self.assertTrue(w.is_distracting("https://m.youtube.com/shorts/x", pats))
        self.assertTrue(w.is_distracting("https://www.tiktok.com/@a/video/1", pats))
        self.assertTrue(w.is_distracting("https://www.instagram.com/reel/abc/", pats))
        self.assertFalse(w.is_distracting("https://www.youtube.com/watch?v=abc", pats))
        self.assertFalse(w.is_distracting("", pats))

    def test_grace_then_mad_then_close(self):
        self.run_for(5)
        self.assertEqual(self.w.status()["mood"], w.SUSPICIOUS)
        self.run_for(6)
        st = self.w.status()
        self.assertEqual(st["mood"], w.MAD)
        self.assertIn("noticed", self.w.pop_events())
        self.assertAlmostEqual(st["remaining"], 59, delta=1.5)
        close = self.run_for(61)
        self.assertEqual(close, 7)
        self.assertIn("closed", self.w.pop_events())

    def test_leaving_calms_and_emits_stopped(self):
        self.run_for(20)
        self.run_for(1, url="https://example.com")
        self.assertEqual(self.w.status()["mood"], w.CALM)
        self.assertIn("stopped", self.w.pop_events())

    def test_quick_hop_away_does_not_reset(self):
        self.run_for(40)
        self.run_for(5, url="https://example.com")
        self.run_for(1)
        self.assertLess(self.w.status()["remaining"], 32)

    def test_long_break_resets(self):
        self.run_for(40)
        self.run_for(31, url="https://example.com")
        self.run_for(1)
        self.assertEqual(self.w.status()["mood"], w.SUSPICIOUS)

    def test_second_chance_is_short(self):
        self.assertEqual(self.run_for(72), 7)
        self.run_for(2, url="about:newtab")
        self.run_for(1)
        st = self.w.status()
        self.assertEqual(st["mood"], w.MAD)
        self.assertLessEqual(st["remaining"], 15)

    def test_unfocused_firefox_does_not_count(self):
        self.run_for(30, focused=False)
        self.assertEqual(self.w.status()["mood"], w.CALM)

    def test_stale_reports_are_ignored(self):
        self.run_for(20)
        for _ in range(20):
            self.clock.now += 1
            self.w.tick()
        self.assertEqual(self.w.status()["mood"], w.CALM)
        self.assertFalse(self.w.status()["connected"])

    def test_pause(self):
        self.w.pause(60)
        self.run_for(40)
        self.assertEqual(self.w.status()["mood"], w.PAUSED)

    def test_sleep_gap_is_clamped(self):
        self.run_for(1)
        self.clock.now += 3600
        self.w.report(SHORTS, 7, True)
        self.w.tick()
        self.assertEqual(self.w.status()["mood"], w.SUSPICIOUS)


class ConfigTest(unittest.TestCase):
    def test_clean_rejects_garbage(self):
        cfg = config._clean({"close_after_seconds": "nope", "scale": 99, "blocked": ["  a.com ", ""], "extra": 1})
        self.assertEqual(cfg["close_after_seconds"], 300)
        self.assertEqual(cfg["scale"], 4.0)
        self.assertEqual(cfg["blocked"], ["a.com"])
        self.assertNotIn("extra", cfg)

    def test_old_settings_move_to_the_animated_cat(self):
        cfg = config._clean(config._migrate({"style": "pixel", "eye_color": "#2A2226", "fur_color": "#F0A35E"}))
        self.assertEqual(cfg["style"], "sprite")
        self.assertEqual(cfg["eye_color"], config.DEFAULTS["eye_color"])
        self.assertEqual(cfg["fur_color"], "#F0A35E")
        again = config._clean(config._migrate(dict(cfg, style="minimal")))
        self.assertEqual(again["style"], "minimal")

    def test_clean_checks_looks(self):
        cfg = config._clean({"fur_color": "red", "second_color": "#abcdef", "pattern": "plaid", "style": "pixel"})
        self.assertEqual(cfg["fur_color"], config.DEFAULTS["fur_color"])
        self.assertEqual(cfg["second_color"], "#ABCDEF")
        self.assertEqual(cfg["pattern"], config.DEFAULTS["pattern"])
        self.assertEqual(cfg["style"], "pixel")


if __name__ == "__main__":
    unittest.main()
