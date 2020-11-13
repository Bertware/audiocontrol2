from ac2.plugins.metadata import MetadataDisplay

import microdotphat
import time
import threading
import logging
from queue import SimpleQueue
from smbus import SMBus
from json import dumps


class MetadataMicroDotPhatDisplay(MetadataDisplay):
    '''
    Show metadata on a Pimoroni Micro Dot pHat 6 character display where each character is 8x5 pixels
    '''

    def __init__(self, params):
        super().__init__()
        self.enabled = self.is_hardware_present()
        # Only enable this plugin if the microdot pHAT hardware is connected
        if not self.enabled:
            logging.warning("MicroDotPhat not detected, microdotphat display module disabled")
            return
        logging.info("MicroDotPhat detected, enabling display output")
        self.current_metadata = None
        self.display_thread_comm_queue = SimpleQueue()
        self.display_thread = MicroDotPhatDisplayThread(self.display_thread_comm_queue, True, True, True, 0.5)
        self.display_thread.start()

    def __del__(self):
        if self.display_thread:
            self.display_thread.exit()

    def notify(self, metadata):
        # Only enable this plugin if the microdot pHAT hardware is connected
        if not self.enabled:
            return
        logging.critical(metadata)
        if self.current_metadata is not None \
                and metadata.playerState == self.current_metadata.playerState \
                and metadata.playerName == self.current_metadata.playerName \
                and metadata.artist == self.current_metadata.artist \
                and metadata.title == self.current_metadata.title:
            logging.critical(self.current_metadata)
            return
        self.display_thread_comm_queue.put(metadata)
        self.current_metadata = metadata

    @staticmethod
    def is_hardware_present():
        return microdotphat.is_connected()

    def __str__(self):
        return "MetadataMicroDotPhatDisplay " + "(enabled)" if self.enabled else "(disabled)"


class MicroDotPhatDisplayThread(threading.Thread):
    def __init__(self, communication_queue, display_playername, display_artist, display_title, brightness):
        threading.Thread.__init__(self)
        self.comm_queue = communication_queue
        self.display_player = display_playername
        self.display_artist = display_artist
        self.display_title = display_title
        self.brightness = brightness
        self.metadata = None
        self.metadata_update_pending = False
        self.active = True

    def __del__(self):
        microdotphat.clear()
        microdotphat.show()

    def is_metadata_update_pending(self):
        return not self.comm_queue.empty()

    def read_queue(self):
        if self.comm_queue.empty():
            return
        while not self.comm_queue.empty():
            self.metadata = self.comm_queue.get()
        self.metadata_update_pending = True
        if self.metadata is None:
            self.active = False

    def exit(self):
        self.active = False

    def run(self):
        player_text = ""
        scrolling_text = ""
        logging.info("Microdotphat display thread started")

        # Show clearly that the display has been enabled
        microdotphat.fill(1)
        microdotphat.show()
        time.sleep(0.5)
        self.display_scrolling("Ready to play!")
        microdotphat.clear()
        microdotphat.show()

        # Auto scroll using a while + time mechanism (no thread)
        while self.active:
            try:
                if self.is_metadata_update_pending():
                    self.read_queue()
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

                # Empty display when not playing
                if not self.metadata or self.metadata.playerState != "playing":
                    microdotphat.clear()
                    microdotphat.show()
                    time.sleep(1)
                    continue

                if not scrolling_text:
                    self.display_static(player_text, duration=5)
                self.display_scrolling(scrolling_text)
                self.display_scrolling(scrolling_text)

            except Exception as e:
                logging.error("Microdotphat display thread encounterd an exception ", e.args)
        logging.info("MMicrodotphat display thread finished")
        microdotphat.clear()
        microdotphat.show()

    def display_static(self, static_text, duration=10):
        if not static_text or self.is_metadata_update_pending():
            return
        microdotphat.clear()
        microdotphat.set_brightness(self.brightness)
        microdotphat.write_string(static_text, kerning=False)
        microdotphat.show()
        # Clear the buffer already, but leave the text on the display
        microdotphat.clear()
        for i in range(duration):
            # This makes the display more responsive to metadata changes
            if self.is_metadata_update_pending():
                return
            time.sleep(1)

    def display_scrolling(self, scrolling_text):
        if not scrolling_text or self.is_metadata_update_pending():
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
            if self.is_metadata_update_pending():
                microdotphat.show()
                return
            microdotphat.write_string(scrolling_text[i:], kerning=False)
            microdotphat.show()
            if i == 0:
                time.sleep(6 * 0.3)
            else:
                time.sleep(0.3)
        # Sleep two seconds after the loop for better readability
        if not self.is_metadata_update_pending():
            time.sleep(1.8)
        microdotphat.clear()
