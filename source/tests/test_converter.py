import unittest
from unittest.mock import patch

import pyxel
from PIL import Image

from source.util.converter import convert_image_to_pyxel_icon_data, convert_rgb_colour_to_pyxel_colour


@patch.object(pyxel, "colors", [
    0x000000, 0x2b335f, 0x7e2072, 0x19959c, 0x8b4852, 0x395c98, 0xa9c1ff, 0xeeeeee,
    0xd4186c, 0xd38441, 0xe9c35b, 0x70c6a9, 0x7696de, 0xa3a3a3, 0xff9798, 0xedc7b0,
])
class ConverterTest(unittest.TestCase):
    """
    The test class responsible for ensuring that images are converted correctly for use as icons.
    Note that we need to patch the default pyxel colours as in v2+, pyxel needs to be initialised to access
    pyxel.colors.
    """
    def test_image_conversion(self):
        """
        Ensure that image data is correctly extracted into the appropriate format for icons.
        """
        # A standard 4x4 image with each in-built pyxel colour and no alpha channel.
        test_image = Image.open("source/tests/resources/test-icon.png")
        pyxel_icon_data = convert_image_to_pyxel_icon_data(test_image)
        self.assertListEqual(["0123", "4567", "89ab", "cdef"], pyxel_icon_data)

        # A standard 4x4 image with each in-built pyxel colour and an alpha channel.
        test_image = Image.open("source/tests/resources/test-icon-alpha.png")
        pyxel_icon_data = convert_image_to_pyxel_icon_data(test_image)
        self.assertListEqual(["0123", "4567", "89ab", "cdef"], pyxel_icon_data)

        # A standard 4x4 image with four repeated in-built pyxel colours and an alpha channel.
        test_image = Image.open("source/tests/resources/test-icon-repeated.png")
        pyxel_icon_data = convert_image_to_pyxel_icon_data(test_image)
        self.assertListEqual(["0000", "4444", "8888", "cccc"], pyxel_icon_data)

    def test_rgb_conversion(self):
        """
        Ensure that the closest in-built pyxel colours are correctly determined for a range of RGB values.
        """
        # In-built pyxel colours.
        self.assertEqual("0", convert_rgb_colour_to_pyxel_colour(0, 0, 0))
        self.assertEqual("1", convert_rgb_colour_to_pyxel_colour(44, 51, 96))
        self.assertEqual("2", convert_rgb_colour_to_pyxel_colour(126, 31, 116))
        self.assertEqual("3", convert_rgb_colour_to_pyxel_colour(24, 149, 156))
        self.assertEqual("4", convert_rgb_colour_to_pyxel_colour(139, 72, 82))
        self.assertEqual("5", convert_rgb_colour_to_pyxel_colour(57, 92, 154))
        self.assertEqual("6", convert_rgb_colour_to_pyxel_colour(170, 193, 255))
        self.assertEqual("7", convert_rgb_colour_to_pyxel_colour(238, 238, 238))
        self.assertEqual("8", convert_rgb_colour_to_pyxel_colour(213, 24, 108))
        self.assertEqual("9", convert_rgb_colour_to_pyxel_colour(211, 132, 65))
        self.assertEqual("a", convert_rgb_colour_to_pyxel_colour(233, 195, 92))
        self.assertEqual("b", convert_rgb_colour_to_pyxel_colour(112, 198, 170))
        self.assertEqual("c", convert_rgb_colour_to_pyxel_colour(117, 150, 222))
        self.assertEqual("d", convert_rgb_colour_to_pyxel_colour(163, 163, 163))
        self.assertEqual("e", convert_rgb_colour_to_pyxel_colour(255, 151, 153))
        self.assertEqual("f", convert_rgb_colour_to_pyxel_colour(237, 199, 176))
        # Other basic colours.
        self.assertEqual("8", convert_rgb_colour_to_pyxel_colour(255, 0, 0))
        self.assertEqual("b", convert_rgb_colour_to_pyxel_colour(0, 255, 0))
        self.assertEqual("1", convert_rgb_colour_to_pyxel_colour(0, 0, 255))
        self.assertEqual("a", convert_rgb_colour_to_pyxel_colour(255, 255, 0))
        self.assertEqual("2", convert_rgb_colour_to_pyxel_colour(128, 0, 128))
        self.assertEqual("9", convert_rgb_colour_to_pyxel_colour(255, 140, 0))


if __name__ == '__main__':
    unittest.main()
