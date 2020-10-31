from ac2.plugins.metadata import MetadataDisplay

import microdotphat
import time
import threading
import logging


class MetadataMicroDotPhatDisplay(MetadataDisplay):
    '''
    Show metadata on a Pimoroni Micro Dot pHat 6 character display where each character is 8x5
    '''

    def __init__(self, display_player=True, display_artist=True, display_title=True, brightness=0.5):
        super().__init__()
        logging.error("MetadataMicroDotPhatDisplay INITIALIZING")
        self.display_thread = MicroDotPhatDisplayThread(display_player, display_artist, display_title, brightness)
        self.display_thread.start()

    def __del__(self):
        if self.display_thread:
            self.display_thread.exit()

    def notify(self, metadata):
        print(metadata)
        self.display_thread.set_metadata(metadata)

    def __str__(self):
        return "http"


class MicroDotPhatDisplayThread(threading.Thread):
    def __init__(self, display_player, display_artist, display_title, brightness):
        threading.Thread.__init__(self)
        self.display_player = display_player
        self.display_artist = display_artist
        self.display_title = display_title
        self.brightness = brightness
        self.metadata = None
        self.metadata_update_pending = False
        self.active = True

    def __del__(self):
        microdotphat.clear()

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.metadata_update_pending = True

    def exit(self):
        self.active = False

    def run(self):
        player_text = ""
        scrolling_text = ""
        logging.error("MICRODOTPHAT DISPLAY THREAD START")

        # Show clearly that the display has been enabled
        microdotphat.fill(1)
        microdotphat.show()
        time.sleep(0.5)
        microdotphat.clear()
        microdotphat.write_string("READY!", kerning=False)
        microdotphat.show()
        time.sleep(1)
        microdotphat.clear()
        microdotphat.show()

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

                self.display_static(player_text, duration=10)
                self.display_scrolling(scrolling_text, loops=2)
            except Exception as e:
                logging.error("MICRODOTPHAT DISPLAY THREAD EXCEPTION ", e)
        logging.info("MICRODOTPHAT DISPLAY THREAD DONE")
        microdotphat.clear()
        microdotphat.show()

    def display_static(self, static_text, duration=10):
        if not static_text:
            return
        logging.error("DISPLAYING STATIC TEXT: " + static_text)
        microdotphat.clear()
        microdotphat.set_brightness(self.brightness)
        microdotphat.write_string(static_text, kerning=False)
        microdotphat.show()
        time.sleep(duration)
        microdotphat.clear()
        microdotphat.show()

    def display_scrolling(self, scrolling_text, loops=1):
        if not scrolling_text:
            return

        display_text = scrolling_text
        # Loop the text a number of times
        if loops > 1:
            for i in range(1, loops):
                display_text += "    " + scrolling_text

        if len(display_text) < 6:
            display_text = display_text.ljust(6, " ")

        microdotphat.clear()
        microdotphat.set_brightness(self.brightness)
        microdotphat.write_string(scrolling_text, kerning=False)

        # The microdotphat has 6 character displays. microdotphat.scroll() moves all text one character
        # The total text length is length(scrolling_text)
        # The first 6 characters fit on the display without scrolling
        # So for each loop, call scroll 'length(scrolling_text) - 6' times
        # This means that, in order to scroll one loop, we need to scroll
        scroll_calls = len(scrolling_text) - 6
        if scroll_calls < 0:
            scroll_calls = 0

        microdotphat.show()
        for i in range(scroll_calls):
            microdotphat.clear()
            microdotphat.write_string(display_text[i:i+7], kerning=False)
            microdotphat.show()
            time.sleep(0.6)
        # Sleep two seconds after the loop for better readability
        time.sleep(2)

        microdotphat.clear()
        microdotphat.show()
