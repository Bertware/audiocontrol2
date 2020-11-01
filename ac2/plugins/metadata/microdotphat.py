from ac2.plugins.metadata import MetadataDisplay

import microdotphat
import time
import threading
import logging
from smbus import SMBus


class MetadataMicroDotPhatDisplay(MetadataDisplay):
    '''
    Show metadata on a Pimoroni Micro Dot pHat 6 character display where each character is 8x5
    '''

    def __init__(self, display_player=True, display_artist=True, display_title=True, brightness=0.5):
        super().__init__()
        self.enabled = self.is_hardware_present()
        # Only enable this plugin if the microdot pHAT hardware is connected
        if not self.enabled:
            logging.warning("MicroDotPhat not detected, microdotphat display module disabled")
            return
        logging.info("MicroDotPhat detected, enabling display output")
        self.current_metadata = None
        self.display_thread = MicroDotPhatDisplayThread(display_player, display_artist, display_title, brightness)
        self.display_thread.start()

    def __del__(self):
        if self.display_thread:
            self.display_thread.exit()

    def notify(self, metadata):
        # Only enable this plugin if the microdot pHAT hardware is connected
        if not self.enabled:
            return
        if self.current_metadata is not None \
                and metadata.playerState == self.current_metadata.playerState \
                and metadata.playerName == self.current_metadata.playerName \
                and metadata.artist == self.current_metadata.artist \
                and metadata.title == self.current_metadata.title:
            return
        self.current_metadata = metadata
        self.display_thread.set_metadata(metadata)

    @staticmethod
    def is_hardware_present():
        bus = SMBus(1)
        try:
            # The microdot pHat uses 3 IS31FL3730 chips located at 0x61, 0x62 and 0x63
            bus.write_byte(0x61, 0)
            bus.write_byte(0x62, 0)
            bus.write_byte(0x63, 0)
            return True
        except:  # exception if read_byte fails, meaning the device isn't connected
            return False

    def __str__(self):
        return "MetadataMicroDotPhatDisplay " + "(enabled)" if self.enabled else "(disabled)"


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
        microdotphat.show()

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.metadata_update_pending = True

    def exit(self):
        self.active = False

    def run(self):
        player_text = ""
        scrolling_text = ""
        logging.info("MICRODOTPHAT DISPLAY THREAD START")

        # Show clearly that the display has been enabled
        microdotphat.fill(1)
        microdotphat.show()
        time.sleep(0.5)
        for word in ("READY", "TO", "PLAY"):
            microdotphat.clear()
            microdotphat.write_string(word, kerning=False)
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

                # Empty display when not playing
                if self.metadata.playerState != "playing":
                    time.sleep(1)
                    continue

                self.display_static(player_text, duration=5)
                self.display_scrolling(scrolling_text)
                self.display_scrolling(scrolling_text)

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

    def display_scrolling(self, scrolling_text):
        if not scrolling_text:
            return

        # The microdotphat has 6 character displays. microdotphat.scroll() moves all text one character
        # The total text length is length(scrolling_text)
        # The first 6 characters fit on the display without scrolling
        # So for each loop, call scroll 'length(scrolling_text) - 6' times
        # This means that, in order to scroll one loop, we need to scroll
        scroll_calls = len(scrolling_text) - 6
        if scroll_calls < 0:
            scroll_calls = 0

        # + 1 since we also need to show offset 0 for the initial text
        for i in range(scroll_calls + 1):
            microdotphat.clear()
            # Stop showing the current text if there is new data available
            if self.metadata_update_pending:
                microdotphat.show()
                return
            microdotphat.write_string(scrolling_text[i:], kerning=False)
            microdotphat.show()
            if i == 0:
                time.sleep(6 * 0.3)
            else:
                time.sleep(0.3)
        # Sleep two seconds after the loop for better readability
        time.sleep(1.8)

        microdotphat.clear()