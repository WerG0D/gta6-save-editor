import unittest
from scripts.watch_ports import relevant


class WatchTest(unittest.TestCase):
    def test_filters(self):
        self.assertTrue(relevant("GTA VI now loads a save file", True))
        self.assertFalse(relevant("Another title supports save slots", True))
        self.assertTrue(relevant("Implement autosave", False))
        self.assertFalse(relevant("Save screenshot as JPEG", False))
        self.assertFalse(relevant("GTAVI renders intro", True))
