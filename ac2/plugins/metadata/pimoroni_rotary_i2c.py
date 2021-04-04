from typing import Dict

import ioexpander

from ac2.plugins.metadata import MetadataDisplay

I2C_ADDR = 0x0F

BRIGHTNESS = 0.25  # Effectively the maximum fraction of the period that the LED will be on
PERIOD = int(255 / BRIGHTNESS)  # Add a period large enough to get 0-255 steps at the desired brightness

PIN_RED = 1  # Breakout board config, breakout port 1 is red led
PIN_GREEN = 7  # Breakout board config, breakout port 7 is green led
PIN_BLUE = 2  # Breakout board config, breakout port 2 is blue led


class RotaryI2CLed(MetadataDisplay):

    def __init__(self, params: Dict[str, str] = None):
        super().__init__()
        encoder_breakout = ioexpander.IOE(i2c_addr=I2C_ADDR)

        encoder_breakout.set_pwm_period(PERIOD)
        encoder_breakout.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker

        # Setup RGB
        encoder_breakout.set_mode(PIN_RED, ioexpander.PWM, invert=True)
        encoder_breakout.set_mode(PIN_GREEN, ioexpander.PWM, invert=True)
        encoder_breakout.set_mode(PIN_BLUE, ioexpander.PWM, invert=True)

        self.encoder_breakout = encoder_breakout

    def notify(self, metadata):
        if metadata.playerState != "playing":
            # off
            self.encoder_breakout.output(PIN_RED, 0)
            self.encoder_breakout.output(PIN_GREEN, 0)
            self.encoder_breakout.output(PIN_BLUE, 0)
        else:
            # White at max brightness, limited by brightness defined above
            self.encoder_breakout.output(PIN_RED, 255)
            self.encoder_breakout.output(PIN_GREEN, 255)
            self.encoder_breakout.output(PIN_BLUE, 255)
