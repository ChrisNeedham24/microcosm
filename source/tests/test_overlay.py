import unittest

from source.display.overlay import Overlay
from source.foundation.models import OverlayType


class OverlayTest(unittest.TestCase):
    """
    The test class for overlay.py.
    """

    def setUp(self) -> None:
        """
        Instantiate a standard Overlay object before each test.
        """
        self.overlay = Overlay()

    def test_toggle_standard(self):
        """
        Ensure that the overlay correctly toggles the Standard overlay.
        """
        # When the Standard and Blessing overlays are being displayed, toggling should not remove the Standard overlay.
        self.overlay.showing = [OverlayType.STANDARD, OverlayType.BLESSING]
        self.overlay.toggle_standard(0)
        self.assertTrue(self.overlay.is_standard())

        # Now with only the Standard overlay, toggling should remove it.
        self.overlay.showing = [OverlayType.STANDARD]
        self.overlay.toggle_standard(0)
        self.assertFalse(self.overlay.is_standard())

        # When displaying the Pause overlay (or a number of others), toggling should not add the Standard overlay.
        self.overlay.showing = [OverlayType.PAUSE]
        self.overlay.toggle_standard(5)
        self.assertFalse(self.overlay.is_standard())

        # When no overlay is being displayed, toggling should add the Standard overlay and set the current turn.
        self.overlay.showing = []
        self.overlay.toggle_standard(5)
        self.assertTrue(self.overlay.is_standard())
        self.assertEqual(5, self.overlay.current_turn)


if __name__ == '__main__':
    unittest.main()
