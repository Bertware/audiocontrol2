import logging
import time
from typing import Dict

import ioexpander

from ac2.plugins.control.controller import Controller

I2C_ADDR = 0x0F

BRIGHTNESS = 0.25  # Effectively the maximum fraction of the period that the LED will be on
PERIOD = int(255 / BRIGHTNESS)  # Add a period large enough to get 0-255 steps at the desired brightness

PIN_RED = 1  # Breakout board config, breakout port 1 is red led
PIN_GREEN = 7  # Breakout board config, breakout port 7 is green led
PIN_BLUE = 2  # Breakout board config, breakout port 2 is blue led

POT_ENC_A = 12
POT_ENC_B = 3
POT_ENC_C = 11

INTERRUPT = 4  # Interrupt connected to GPIO 4


class Rotary(Controller):

    def __init__(self, params: Dict[str, str] = None):
        super().__init__()
        encoder_breakout = ioexpander.IOE(i2c_addr=I2C_ADDR, interrupt_pin=INTERRUPT)

        # Swap the interrupt pin for the Rotary Encoder breakout
        if I2C_ADDR == 0x0F:
            encoder_breakout.enable_interrupt_out(pin_swap=True)

        encoder_breakout.setup_rotary_encoder(1, POT_ENC_A, POT_ENC_B, pin_c=POT_ENC_C)

        encoder_breakout.set_pwm_period(PERIOD)
        encoder_breakout.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker

        # Setup RGB
        encoder_breakout.set_mode(PIN_RED, ioexpander.PWM, invert=True)
        encoder_breakout.set_mode(PIN_GREEN, ioexpander.PWM, invert=True)
        encoder_breakout.set_mode(PIN_BLUE, ioexpander.PWM, invert=True)

        # White at max brightness, limited by brightness defined above
        encoder_breakout.output(PIN_RED, 255)
        encoder_breakout.output(PIN_GREEN, 255)
        encoder_breakout.output(PIN_BLUE, 255)

        self.encoder_breakout = encoder_breakout
        self._last_value = self.encoder_breakout.read_rotary_encoder(1)

    def run(self):
        while 1:
            # Act on interrupt
            if self.encoder_breakout.get_interrupt():
                count = self.encoder_breakout.read_rotary_encoder(1)
                self.encoder_breakout.clear_interrupt()
                # The encoder gives an absolute value/count, determine the change
                change = self.calc_change_percent(count)
                self._last_value = count
                if self.volumecontrol is not None:
                    self.volumecontrol.change_volume_percent(change)
            # Check 30x per second
            time.sleep(1.0 / 30)

    def calc_change_percent(self, count):
        change = count - self._last_value
        # Limit volume change to prevent volume jumps in case the encoder has any bugs.
        if change < -3:
            change = -3
        if change > 3:
            change = 3
        return change
