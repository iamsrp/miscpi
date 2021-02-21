#!/usr/bin/python

from __future__ import print_function

import RPi.GPIO as GPIO
import numpy    as np
import pyaudio
import struct
import time

from scipy.fftpack import fft

# ----------------------------------------------------------------------

_PRINT = False
#_PRINT = True

# The pins; left and right channels
#_PINS = ((26, 19, 13,  6,  5, 11,  9, 10, 22, 27),
#         (17,  4,  3,  2, 25, 24, 23, 18, 15, 14))
_PINS = (( 2,  3,  4, 17, 27, 22, 10,  9, 11,  5),
         ( 6, 13, 19, 26, 25,  8,  7, 16, 20, 21))
#_PINS = ((  5, 11,  9, 10, 22, 27, 17,  4,  3,  2),
#         ( 21, 20, 16,  7,  8, 25, 26, 19, 13,  6))
assert len(_PINS[0]) == len(_PINS[1])
_NUM_OUT = len(_PINS[0])

# Constants for the microphone input.

# How much to read at a time
_CHUNK = 1024 * 2

# The sample rate, in kHz
_RATE = 44100

# How many channels
_CHANNELS = 1

# The PWM frequency
_PWM_HZ = 500

# ----------------------------------------------------------------------

def init_gpio():
    """
    Set up the GPIO ports and put them into the right state.
    """
    # Set the pin numbering to be that of the GPIOs, not the pins on the board. And
    # turn off noisy warnings.
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Init the GPIO ports etc.
    pwm = list()
    for side in _PINS:
        pwm_side = list()
        pwm.append(pwm_side)
        for pin in side:
            GPIO.setup (pin, GPIO.OUT)
            GPIO.output(pin, False)

            # Set up the pulse-wide modulalisation
            pwm_pin = GPIO.PWM(pin, _PWM_HZ)
            pwm_pin.start(0)
            pwm_side.append(pwm_pin)

    # And give back the PWMs
    return pwm


def open_microphone():
    """
    Open the audio stream from the microphone.
    """    
    return pyaudio.PyAudio().open(
        format=pyaudio.paInt16,
        channels=_CHANNELS,
        rate=_RATE,
        input=True,
        output=True,
        frames_per_buffer=_CHUNK,
    )


def main():
    """
    Entry point.
    """
    # Get the PWM controllers
    pwms = init_gpio()

    # How many outputs for the FFT?
    xf = np.linspace(0, _RATE, _CHUNK)
    count = len(xf)

    # How many outputs to average over to set the PWM
    bucket_start = count * 0.1
    bucket_size  = (count - bucket_start) / _NUM_OUT

    # Start streaming!
    stream = open_microphone()

    # And around we go...
    while True:
        # Pull in the next sample
        data     = stream.read(_CHUNK, exception_on_overflow=False)
        data_int = struct.unpack(str(2 * _CHUNK) + 'B', data)

        # Compute the FFT
        data_fft = fft(data_int)

        # Normalise it
        yf = np.abs(data_fft[0:_CHUNK]) / (128 * _CHUNK)

        # Accumulate and set the duty cycle of each pin
        for i in range(_NUM_OUT):
            # Accumulate from here to here
            freq  = xf[int(i * bucket_size + bucket_start)]
            start = int(i       * bucket_size + bucket_start)
            end   = int((i + 1) * bucket_size + bucket_start)

            # Change to duty cycle to be a value in between 0 and 100 (percent)
            duty_cycle = \
                int(
                    np.max((
                        0.0,
                        np.min((
                            100.0,
                            (np.mean(yf[start:end]) - 0.01) * 10000
                        ))
                    ))
                )
            pwms[0][i].ChangeDutyCycle(duty_cycle)
            pwms[1][i].ChangeDutyCycle(duty_cycle)
            if _PRINT:
                print("%d %d %d" % (i, freq, duty_cycle))
        if _PRINT:
            print('')
        

if __name__ == "__main__":
    main()
