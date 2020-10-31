from ac2.plugins.metadata import MetadataDisplay

import scrollphathd
import time
import threading
import logging
from scrollphathd.fonts import font3x5


class MetadataScrollPhatHdDisplay(MetadataDisplay):
    '''
    Show metadata on a Pimoroni Scroll Phat HD 17x7 display
    '''

    def __init__(self, display_player=True, display_artist=True, display_title=True, brightness=0.5):
        super().__init__()
        self.current_metadata = None
        self.display_thread = ScrollPhatHdDisplayThread(display_player, display_artist, display_title, brightness)
        self.display_thread.start()

    def __del__(self):
        if self.display_thread:
            self.display_thread.exit()

    def notify(self, metadata):
        if self.current_metadata is not None \
                and metadata.playerName == self.current_metadata.playerName \
                and metadata.artist == self.current_metadata.artist \
                and metadata.title == self.current_metadata.title:
            return
        self.current_metadata = metadata
        self.display_thread.set_metadata(metadata)

    def __str__(self):
        return "MetadataScrollPhatHdDisplay"


class ScrollPhatHdDisplayThread(threading.Thread):
    def __init__(self, display_player, display_artist, display_title, brightness):
        threading.Thread.__init__(self)
        self.display_player = display_player
        self.display_artist = display_artist
        self.display_title = display_title
        self.brightness = brightness
        self.metadata = None
        self.metadata_update_pending = False
        self.active = True
        scrollphathd.clear()

    def __del__(self):
        scrollphathd.clear()

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.metadata_update_pending = True

    def exit(self):
        self.active = False

    def run(self):
        player_text = ""
        scrolling_text = ""
        scrollphathd.fill(brightness=self.brightness)
        scrollphathd.show()
        time.sleep(0.5)
        scrollphathd.clear()
        scrollphathd.show()
        scrollphathd.write_string("READY!", y=1, font=font3x5)
        scrollphathd.show()
        time.sleep(1)
        scrollphathd.clear()
        scrollphathd.show()

        logging.info("SCROLLPHAT DISPLAY THREAD START")
        # Auto scroll using a while + time mechanism (no thread)
        while self.active:
            try:
                if self.metadata_update_pending:
                    # Write the string in the buffer and
                    # set a more eye-friendly default brightness
                    scrolling_text = ""
                    player_text = ""
                    if self.display_player and self.metadata.playerName:
                        player_text += self.metadata.playerName
                    if self.display_artist and self.metadata.artist:
                        scrolling_text += self.metadata.artist
                    if self.display_artist and self.metadata.artist and self.display_title and self.metadata.title:
                        scrolling_text += " - "
                    if self.display_title and self.metadata.title:
                        scrolling_text += self.metadata.title

                    player_text = player_text.upper()
                    scrolling_text = scrolling_text.upper()
                    self.metadata_update_pending = False

                self.display_static(player_text, duration=5)
                self.display_scrolling(scrolling_text)
                self.display_scrolling(scrolling_text)
            except Exception as e:
                logging.error("SCROLLPHAT DISPLAY THREAD EXCEPTION ", e)
        logging.info("SCROLLPHAT DISPLAY THREAD DONE")
        scrollphathd.clear()

    def display_static(self, static_text, duration=10):
        if not static_text:
            return
        logging.error("DISPLAYING STATIC TEXT: " + static_text)
        scrollphathd.write_string(static_text, y=1, font=font3x5, brightness=self.brightness)
        scrollphathd.show()
        time.sleep(duration)
        scrollphathd.clear()
        scrollphathd.show()

    def display_scrolling(self, scrolling_text):
        if not scrolling_text:
            return

        scrollphathd.write_string(scrolling_text, y=1, font=font3x5, brightness=self.brightness)
        scrollphathd.show()
        time.sleep(0.1)

        # The font is 3x5 with one column as a space behind every character.
        # scrollphathd.scroll() moves all text one pixel
        # The total text length is 4 x length(scrolling_text), including spaces
        # The first 17 columns fit on the display without scrolling
        # The last space should not be scrolled
        # This means that, in order to scroll one loop, we need to scroll
        scroll_calls = 4 * len(scrolling_text) - 17 - 1
        if scroll_calls < 0:
            scroll_calls = 0

        for i in range(scroll_calls):
            scrollphathd.scroll()
            scrollphathd.show()
            time.sleep(0.1)
        # Sleep two seconds after the loop for better readability
        time.sleep(2)

        scrollphathd.clear()
        scrollphathd.show()
