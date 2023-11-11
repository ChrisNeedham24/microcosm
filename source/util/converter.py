import typing

import pyxel
from PIL import Image, PyAccess


def convert_image_to_pyxel_icon_data(image: Image) -> typing.List[str]:
    """
    Convert the supplied Pillow Image data into the format required for the pyxel.icon() method.

    Some details on the required format are below:
    - The format required by Pyxel isn't immediately apparent, and had to be reverse engineered from the actual Rust
      code from the Pyxel repository.
    - Pyxel expects a list of strings, each representing a row of pixels in the image.
    - Since each string element represents a row of pixels, each character in each string represents a single pixel.
    - A single pixel can have a value from 0 to f, in base 16, where each available value represents an in-built Pyxel
      colour, with the mappings and hex colours below:
      0. Black (0000000) NOTE: Black is a special case in that it does not render at all for icons; it is just
        transparent.
      1. Navy (2b335f)
      2. Purple (7e2072)
      3. Green (19959c)
      4. Brown (8b4852)
      5. Dark blue (395c98)
      6. Light blue (a9c1ff)
      7. White (eeeeee)
      8. Red (d4186c)
      9. Orange (d38441)
      a. Yellow (e9c35b)
      b. Lime (70c6a9)
      c. Cyan (7696de)
      d. Grey (a3a3a3)
      e. Pink (ff9798)
      f. Peach (edc7b0)

    For example, a 5x3 image with a red row, a yellow row, and a purple row would yield ["88888", "aaaaa", "22222"].
    :param image: The Pillow Image to be converted.
    :return: A list of strings representing the image, in the appropriate format.
    """
    icon_pixels: PyAccess = image.load()
    icon_colours: typing.List[str] = []
    # Rather than determine the correct pyxel colour for every pixel individually, we maintain a dictionary of existing
    # mappings, so we do not need to reconvert RGB values that have already been converted.
    rgb_pyxel_mappings: typing.Dict[typing.Tuple[int, int, int], str] = {}
    for y in range(image.height):
        # Initialise the row as an empty string, with each character added to it being a pixel in the row.
        row_colours: str = ""
        for x in range(image.width):
            # Handle images with and without alpha channels.
            if len(pixel := icon_pixels[x, y]) == 3:
                r, g, b = pixel
            else:
                # We ignore the alpha channel here because it is not required.
                r, g, b, _ = pixel
            # If we've already determined the colour for these RGB values, just get it from the dictionary.
            if (r, g, b) in rgb_pyxel_mappings:
                row_colours += rgb_pyxel_mappings[(r, g, b)]
            else:
                # Otherwise, determine which in-built pyxel colour is closest to the RGB values for this pixel.
                closest_colour: str = convert_rgb_colour_to_pyxel_colour(r, g, b)
                rgb_pyxel_mappings[(r, g, b)] = closest_colour
                row_colours += closest_colour
        # Once every pixel in the row has been converted, add the fully-formed string to the list.
        icon_colours.append(row_colours)
    return icon_colours


def convert_rgb_colour_to_pyxel_colour(red: int, green: int, blue: int) -> str:
    """
    Convert the given RGB values into the closest in-built pyxel colour.
    :param red: The red component of the pixel, from 0 to 255.
    :param green: The green component of the pixel, from 0 to 255.
    :param blue: The blue component of the pixel, from 0 to 255.
    :return: The hex string representation of the in-built pyxel colour that these RGB values are closest to. Please
    refer to the mappings detailed in the documentation for the above method for additional information.
    """
    closest_colour: str = "0"
    closest_colour_dist: float = 99999  # 99999 is arbitrary, but no distance will ever exceed this.
    for i in range(pyxel.NUM_COLORS):
        # The individual component distances and the overall distance calculations below are adapted from the actual
        # Rust code from the pyxel repository, specifically the color_dist() function in image.rs in the pyxel-core
        # crate.
        r_dist = (red - (pyxel.colors[i] >> 16 & 0xff)) * 0.30
        g_dist = (green - (pyxel.colors[i] >> 8 & 0xff)) * 0.59
        b_dist = (blue - (pyxel.colors[i] & 0xff)) * 0.20
        colour_dist = pow(r_dist, 2) + pow(g_dist, 2) + pow(b_dist, 2)
        if colour_dist < closest_colour_dist:
            # Convert our integer index into hex so that it fits with the required format.
            closest_colour = f"{i:x}"
            closest_colour_dist = colour_dist
    return closest_colour
