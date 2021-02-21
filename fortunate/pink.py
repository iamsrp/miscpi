"""
Basic wrappers around the PIL library, for me.
"""
from   abc                  import abstractmethod
from   PIL                  import Image, ImageDraw, ImageFont, ImageColor, ImageOps

import logging
import string

class _Font():
    """
    How we get fonts, for any size.
    """
    def __init__(self, filename):
        """
        :param filename: The path to the font file.
        """
        # Store the font information by size
        self._by_size  = {}
        self._filename = filename


    def by_size(self, size):
        """
        Get the font by the given size, or `None` if we can't.
        """
        # Lazily load
        if size not in self._by_size:
            try:
                # Grab the font
                self._by_size[size] = ImageFont.truetype(self._filename, size)
            except Exception as e:
                # Best effort
                logging.warning("Could not load %s with size %d: %s",
                                self._filename, size, e)
                self._by_size[size] = None

        # And give it back
        return self._by_size[size]


class Display():
    """
    Interface class for different eInk displays.
    """
    @property
    @abstractmethod
    def mode(self):
        """
        The PIL concept mode for the display.
        """
        pass


    @property
    @abstractmethod
    def width(self):
        """
        The display width.
        """
        pass


    @property
    @abstractmethod
    def height(self):
        """
        The display height.
        """
        pass


    @property
    @abstractmethod
    def white(self):
        """
        The display's colour white.
        """
        pass


    @property
    @abstractmethod
    def black(self):
        """
        The display's colour white.
        """
        pass


    @abstractmethod
    def display_image(self, image):
        """
        Display the given PIL Image.

        :param image: The PIL `Image`.
        :type image:  Image
        """
        pass


class Pink():
    """
    When I know what this does I will fill this in.
    """
    # Min and max font sizes
    _MIN_FONT_SIZE =   1
    _MAX_FONT_SIZE = 128

    def __init__(self,
                 display,
                 frame_width  =1,
                 font_filename="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        """
        :param font_filename: The path to the TTF font to use
        """
        # The Display to use
        self._display = display

        # The width of the border
        self._frame_width = int(frame_width)

        # The font we will use
        self._font = _Font(font_filename)


    def write(self, text):
        """
        Write the text the the center of the screen.
        """
        image = Image.new(self._display.mode,
                          (self._display.width, self._display.height))
        draw  = ImageDraw.Draw(image)

        # Draw a frame
        if self._frame_width > 0:
            draw.rectangle((0,
                            0,
                            self._display.width,
                            self._display.height),
                           fill=self._display.black)
        draw.rectangle((self._frame_width,
                        self._frame_width,
                        self._display.width  - 2*self._frame_width,
                        self._display.height - 2*self._frame_width),
                       fill=self._display.white)

        # Our extents
        max_width  = (self._display.width  - 2*self._frame_width - 2)
        max_height = (self._display.height - 2*self._frame_width - 2)

        # And the text. We break it up by lines.
        lines = tuple(line.strip() for line in text.split('\n'))

        # Do a binary search to determine the maximum size which we can display
        # it with. We have the +1 in the test since the steps are integers and
        # so the "midpoint" of 2 and 3 will be 2.
        (left, right) = (self._MIN_FONT_SIZE, self._MAX_FONT_SIZE)
        font = None
        while left + 1 < right:
            # Get the font which is the midpoint size
            mid = (right - left) // 2 + left
            logging.info("Searching %d in [%d,%d]", mid, left, right)

            font = self._font.by_size(mid)
            if font is None:
                break

            # How big for the text?
            width  = 0
            height = 0
            for line in lines:
                (w, h) = font.getsize(line)
                width  = max(w, width)
                height = max(h, height)

            # And recurse down. The total height will be the max line height
            # times the number of lines.
            if width <= max_width and height * len(lines) <= max_height:
                left  = mid
            else:
                right = mid

        # Anything?
        font = self._font.by_size(left)
        if font is None:
            raise ValueError("No font")

        # Draw it using the font
        mid_x = self._display.width  // 2
        mid_y = self._display.height // 2
        for (i, line) in enumerate(lines):
            (width, _) = font.getsize(line)
            x = mid_x - width // 2
            y = mid_y + (i - len(lines) / 2) * height
            draw.text((x, y), line, fill=self._display.black, font=font)

        # Display the image which we drew
        self._display.display_image(image)


class SSD1675Display(Display):
    def __init__(self):
        # Specific imports
        from   adafruit_epd.ssd1675 import Adafruit_SSD1675
        import digitalio
        import busio
        import board

        # We need this lot to set up the screen
        spi  = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        ecs  = digitalio.DigitalInOut(board.CE0)
        dc   = digitalio.DigitalInOut(board.D22)
        srcs = None
        rst  = digitalio.DigitalInOut(board.D27)
        busy = digitalio.DigitalInOut(board.D17)

        self._display = Adafruit_SSD1675(122, 250,
                                         spi,
                                         cs_pin    =ecs,
                                         dc_pin    =dc,
                                         sramcs_pin=srcs,
                                         rst_pin   =rst,
                                         busy_pin  =busy,)
        self._display.rotation = 1


    @property
    def mode(self):
        """
        The PIL concept mode for the display.
        """
        return "RGB"


    @property
    def width(self):
        """
        The display width.
        """
        return self._display.width


    @property
    def height(self):
        """
        The display height.
        """
        return self._display.height


    @property
    def white(self):
        """
        The display's colour white.
        """
        return ImageColor.getrgb("WHITE")


    @property
    def black(self):
        """
        The display's colour white.
        """
        return ImageColor.getrgb("BLACK")


    def display_image(self, image):
        self._display.image(image)
        self._display.display()



class InkyDisplay(Display):
    def __init__(self):
        # Specific imports
        from inky.auto import auto

        self._display = inky_display = auto(ask_user=True, verbose=True)


    @property
    def mode(self):
        """
        The PIL concept mode for the display.
        """
        return "P"


    @property
    def width(self):
        """
        The display width.
        """
        return self._display.resolution[0]


    @property
    def height(self):
        """
        The display height.
        """
        return self._display.resolution[1]


    @property
    def white(self):
        """
        The display's colour white.
        """
        return self._display.WHITE


    @property
    def black(self):
        """
        The display's colour white.
        """
        return self._display.BLACK


    def display_image(self, image):
        self._display.set_image(image)
        self._display.show()

# --------------------------------------------------------

if __name__ == "__main__":
    for cls in (SSD1675Display, InkyDisplay):
        print("Trying %s" % (cls,))
        try:
            p = Pink(cls())
            p.write(
"""\
Hello!
This is a test...
...of my display code."""
            )
        except Exception as e:
            print("%s failed: %s" % (cls, e))
        print()
