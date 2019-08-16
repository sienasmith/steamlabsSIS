global GPIO, PWM
from periphery import GPIO, PWM, GPIOError
from adafruit_motor import servo
import pulseio
import time
import board
import argparse
import sys
import os
import time
import threading


# create a PWMOut object on Pin PWM3.
pwm1 = pulseio.PWMOut(board.PWM1, duty_cycle=2 ** 15, frequency=50)
pwm2 = pulseio.PWMOut(board.PWM2, duty_cycle=2 ** 15, frequency=50)
pwm3 = pulseio.PWMOut(board.PWM3, duty_cycle=2 ** 15, frequency=50)

# Create a servo object, my_servo.
my_servo1 = servo.Servo(pwm1)
my_servo2 = servo.Servo(pwm2)
my_servo3 = servo.Servo(pwm3)



while True:
    print("Turning!")
    for angle in range(0, 180, 5):  # 0 - 180 degrees, 5 degrees at a time.
    # print(flag.isSet())
      self.ui.my_servo3.angle = 90 #C
    # flag.wait()
      self.ui.my_servo1.angle = angle / 2
      self._ui.my_servo2.angle = angle #NC
      self.ui.my_servo3.angle = 141  #C
      time.sleep(0.05)
    # print("Thread running.")
    print("Turning back!")
    for angle in range(180, 0, -5): # 180 - 0 degrees, 5 degrees at a time.
    # print(flag.isSet())
      self.ui.my_servo3.angle = 90
    # flag.wait()
      self.ui.my_servo1.angle = angle / 2
      self._ui.my_servo2.angle = angle #NC
      self.ui.my_servo3.angle = 39       #C
      time.sleep(0.05)


