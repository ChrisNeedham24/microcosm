import pyxel


def draw_paragraph(x_start: int, y_start: int, text: str, line_length: int, colour: int = pyxel.COLOR_WHITE) -> None:
    """
    Render text to the screen while automatically accounting for line breaks.
    :param x_start: x of the text's starting position.
    :param y_start: y of the text's starting position.
    :param text: The full text to draw.
    :param line_length: The maximum character length of each line.
    :param colour: The colour of the text to draw.
    """
    text_to_draw = ""

    for word in text.split():
        # Iterate through each word and check if there's enough space on the current line to add it. Otherwise,
        # draw what we have so far and go to the next line.
        if len(text_to_draw) + len(word) <= line_length:
            text_to_draw += word
        else:
            pyxel.text(x_start, y_start, text_to_draw, colour)
            text_to_draw = word
            # Increment the y position of the text at the end of each line.
            y_start += 6

        # Add a space after each word (so that the reader doesn't run out of breath).
        text_to_draw += " "

    # Draw any remaining text to the final line.
    pyxel.text(x_start, y_start, text_to_draw, colour)
