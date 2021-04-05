import logging
import threading
import time
from queue import SimpleQueue

import microdotphat
import scrollphathd

from ac2.plugins.metadata import MetadataDisplay


class PimoroniMetadataDisplay(MetadataDisplay):

    def __init__(self, params):
        super().__init__()
        self.enabled = self.is_hardware_present()
        # Only enable this plugin if the microdot pHAT hardware is connected
        if not self.enabled:
            logging.warning("MicroDotPhat not detected, microdotphat display module disabled")
            return
        logging.info("MicroDotPhat detected, enabling display output")
        self.current_metadata = None
        self.display_thread_metadata_queue = SimpleQueue()
        self.display_thread_volume_queue = SimpleQueue()
        self.display_thread = self.get_async_display_manager()
        self.display_thread.start()

    def __del__(self):
        self.display_thread_metadata_queue.put(None)
        self.display_thread_volume_queue.put(None)
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
            logging.critical(self.current_metadata)
            return
        self.display_thread_metadata_queue.put(metadata)
        self.current_metadata = metadata

    def update_volume(self, volume_level):
        # volume change
        self.display_thread_volume_queue.put(volume_level)

    def is_hardware_present(self):
        return False  # Implement this in actual display class.

    def get_async_display_manager(self):
        pass  # Implement this in the actual display class.

    def __str__(self):
        return "PimoroniMetadataDisplay " + "(enabled)" if self.enabled else "(disabled)"


class ScrollphatHdDisplay(PimoroniMetadataDisplay):
    """
    Show metadata on a Pimoroni Scroll pHat HD 17x7 led display
    """

    def is_hardware_present(self):
        return ScrollPhatHdDisplayManager.is_hardware_present()

    def get_async_display_manager(self):
        return ScrollPhatHdDisplayManager(self.display_thread_metadata_queue,
                                          self.display_thread_volume_queue,
                                          True, True, True, 0.5)

    def __str__(self):
        return "ScrollphatHdDisplay, " + super(PimoroniMetadataDisplay).__str__()


class MicrodotPhatDisplay(PimoroniMetadataDisplay):
    """
    Show metadata on a Pimoroni Micro Dot pHat 6 character display where each character is 8x5 pixels
    """

    def is_hardware_present(self):
        return MicrodotPhatDisplayManager.is_hardware_present()

    def get_async_display_manager(self):
        return MicrodotPhatDisplayManager(self.display_thread_metadata_queue,
                                          self.display_thread_volume_queue,
                                          True, True, True, 0.5)

    def __str__(self):
        return "MicrodotPhatDisplay, " + super(PimoroniMetadataDisplay).__str__()


class PimoroniDisplayManager(threading.Thread):
    def __init__(self, metadata_queue, volume_queue, display_playername, display_artist, display_title, brightness):
        threading.Thread.__init__(self)
        self.metadata_queue = metadata_queue
        self.volume_queue = volume_queue
        self.display_player = display_playername
        self.display_artist = display_artist
        self.display_title = display_title
        self.brightness = brightness
        self.volume_level = 0
        self.metadata = None
        self.active = True

    def __del__(self):
        microdotphat.clear()
        microdotphat.show()

    def is_metadata_update_pending(self):
        return not self.metadata_queue.empty()

    def is_volume_update_pending(self):
        return not self.volume_queue.empty()

    def is_update_pending(self):
        return self.is_volume_update_pending() or self.is_metadata_update_pending()

    def read_metadata_queue(self):
        if self.metadata_queue.empty():
            return
        while not self.metadata_queue.empty():
            self.metadata = self.metadata_queue.get()
        if self.metadata is None:
            self.active = False

    def read_volume_queue(self):
        if self.volume_queue.empty():
            return
        while not self.volume_queue.empty():
            self.volume_level = self.volume_queue.get()
        if self.volume_level is None:
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
                    self.read_metadata_queue()
                    scrolling_text = ""
                    player_text = ""

                    if self.display_player and self.metadata.playerName:
                        player_text += self.metadata.playerName if self.metadata.playerName != "alsaloop" else "aux"
                    if self.display_artist and self.metadata.artist:
                        scrolling_text += self.metadata.artist
                    if self.display_artist and self.metadata.artist and self.display_title and self.metadata.title:
                        scrolling_text += " - "
                    if self.display_title and self.metadata.title:
                        scrolling_text += self.metadata.title

                    player_text = player_text.upper()
                    scrolling_text = scrolling_text.upper()

                if self.is_volume_update_pending():
                    self.read_volume_queue()
                    self.display_static(f"VOL{self.volume_level: 3}", duration=3)
                    continue

                # Empty display when not playing
                if not self.metadata or self.metadata.playerState != "playing":
                    microdotphat.clear()
                    microdotphat.show()
                    self.aware_sleep(1)
                    continue

                # if not scrolling_text:
                self.display_scrolling(scrolling_text)
                self.display_static(player_text, duration=10)
                self.display_scrolling(scrolling_text)

            except Exception as e:
                logging.error("Microdotphat display thread encounterd an exception ", e.args)
        logging.info("Microdotphat display thread finished")
        microdotphat.clear()
        microdotphat.show()

    def aware_sleep(self, duration_seconds: float):
        """
        Sleep, but skip as soon as there is a change in the data.
        """
        for i in range(round(duration_seconds * 10)):
            if self.is_update_pending():
                return
            time.sleep(0.1)
        return

    def display_scrolling(self, text):
        pass  # Implement in display classes.

    def display_static(self, text, duration):
        pass  # Implement in display classes.


class MicrodotPhatDisplayManager(PimoroniDisplayManager):
    def display_static(self, static_text, duration=10):
        if not static_text or self.is_update_pending():
            return
        microdotphat.clear()
        microdotphat.set_brightness(self.brightness)
        microdotphat.write_string(static_text, kerning=False)
        microdotphat.show()
        # Clear the buffer already, but leave the text on the display
        microdotphat.clear()
        self.aware_sleep(duration)

    def display_scrolling(self, scrolling_text):
        if not scrolling_text or self.is_update_pending():
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
            if self.is_update_pending():
                microdotphat.show()
                return
            microdotphat.write_string(scrolling_text[i:], kerning=False)
            microdotphat.show()
            if i == 0:
                self.aware_sleep(4 * 0.2)
            else:
                self.aware_sleep(0.2)
        # Sleep two seconds after the loop for better readability
        self.aware_sleep(1.8)
        microdotphat.clear()

    def __del__(self):
        microdotphat.clear()
        microdotphat.show()

    @staticmethod
    def is_hardware_present():
        return microdotphat.is_connected()


class ScrollPhatHdDisplayManager(PimoroniDisplayManager):
    def display_static(self, static_text, duration=10):
        from scrollphathd.fonts import font3x5
        if not static_text:
            return
        scrollphathd.write_string(static_text, y=1, font=font3x5, brightness=self.brightness)
        scrollphathd.show()
        self.aware_sleep(duration)
        scrollphathd.clear()
        scrollphathd.show()

    def display_scrolling(self, scrolling_text):
        from scrollphathd.fonts import font3x5
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
            # Quick exit when new metadata is available
            if self.is_update_pending():
                scrollphathd.clear()
                scrollphathd.show()
                return
            scrollphathd.scroll()
            scrollphathd.show()
            time.sleep(0.1)
        # Sleep two seconds after the loop for better readability
        self.aware_sleep(2)

        scrollphathd.clear()
        scrollphathd.show()

    @staticmethod
    def is_hardware_present():
        return scrollphathd.is_connected()

    def __del__(self):
        scrollphathd.clear()
        scrollphathd.show()
