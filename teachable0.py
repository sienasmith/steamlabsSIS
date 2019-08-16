
#!/usr/bin/env python
#
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import board
import argparse
import sys
import os
import time
import threading

from collections import deque, Counter
from functools import partial

os.environ['XDG_RUNTIME_DIR']='/run/user/1000'

from embedding import kNNEmbeddingEngine
from PIL import Image

import gstreamer

def detectPlatform():
  try:
    model_info = open("/sys/firmware/devicetree/base/model").read()
    if 'Raspberry Pi' in model_info:
      print("Detected Raspberry Pi.")
      return "raspberry"
    if 'MX8MQ' in model_info:
      print("Detected EdgeTPU dev board.")
      return "devboard"
    return "Unknown"
  except:
    print("Could not detect environment. Assuming generic Linux.")
    return "unknown"


class UI(object):
  """Abstract UI class. Subclassed by specific board implementations."""
  def __init__(self):
    self._button_state = [False for _ in self._buttons]
    current_time = time.time()
    self._button_state_last_change = [current_time for _ in self._buttons]
    self._debounce_interval = 0.1 # seconds

  def setOnlyLED(self, index):
    for i in range(len(self._LEDs)): self.setLED(i, False)
    if index is not None: self.setLED(index, True)

  def isButtonPressed(self, index):
    buttons = self.getButtonState()
    return buttons[index]

  def setLED(self, index, state):
    raise NotImplementedError()

  def getButtonState(self):
    raise NotImplementedError()

  def getDebouncedButtonState(self):
    t = time.time()
    for i,new in enumerate(self.getButtonState()):
      if not new:
        self._button_state[i] = False
        continue
      old = self._button_state[i]
      if ((t-self._button_state_last_change[i]) >
             self._debounce_interval) and not old:
        self._button_state[i] = True
      else:
        self._button_state[i] = False
      self._button_state_last_change[i] = t
    return self._button_state

  def testButtons(self):
    while True:
      for i in range(5):
        self.setLED(i, self.isButtonPressed(i))
      print('Buttons: ', ' '.join([str(i) for i,v in
          enumerate(self.getButtonState()) if v]))
      time.sleep(0.01)

  def wiggleLEDs(self, reps=3):
    for i in range(reps):
      for i in range(5):
        self.setLED(i, True)
        time.sleep(0.05)
        self.setLED(i, False)


class UI_Keyboard(UI):
  def __init__(self):
    global keyinput
    import keyinput

    # Layout of GPIOs for Raspberry demo
    self._buttons = ['q', '1' , '2' , '3', '4']
    self._LEDs = [None]*5
    super(UI_Keyboard, self).__init__()

  def setLED(self, index, state):
    pass

  def getButtonState(self):
    pressed_chars = set()
    while True:
      char = keyinput.get_char()
      if not char : break
      pressed_chars.add(char)

    state = [b in pressed_chars for b in self._buttons]
    return state


class UI_Raspberry(UI):
  def __init__(self):
    # Only for RPi3: set GPIOs to pulldown
    global rpigpio
    import RPi.GPIO as rpigpio
    rpigpio.setmode(rpigpio.BCM)

    # Layout of GPIOs for Raspberry demo
    self._buttons = [16 , 6 , 5 , 24, 27]
    self._LEDs = [20, 13, 12, 25, 22]

    # Initialize them all
    for pin in self._buttons:
      rpigpio.setup(pin, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
    for pin in self._LEDs:
      rpigpio.setwarnings(False)
      rpigpio.setup(pin, rpigpio.OUT)
    super(UI_Raspberry, self).__init__()

  def setLED(self, index, state):
    return rpigpio.output(self._LEDs[index],
           rpigpio.LOW if state else rpigpio.HIGH)

  def getButtonState(self):
    return [rpigpio.input(button) for button in self._buttons]


class UI_EdgeTpuDevBoard(UI):
  def __init__(self):
    global GPIO, PWM
    from periphery import GPIO, PWM, GPIOError
    from adafruit_motor import servo
    import pulseio

# create a PWMOut object on Pin PWM3.
#pwm1 = pulseio.PWMOut(board.PWM1, duty_cycle=2 ** 15, frequency=50)
#pwm2 = pulseio.PWMOut(board.PWM2, duty_cycle=2 ** 15, frequency=50)
    pwm3 = pulseio.PWMOut(board.PWM3, duty_cycle=2 ** 15, frequency=50)

# Create a servo object, my_servo.
#my_servo1 = servo.Servo(pwm1)
#my_servo2 = servo.Servo(pwm2)
    self.my_servo3 = servo.Servo(pwm3)

    def initPWM(pin):
      pwm = PWM(pin, 0)
      pwm.frequency = 1e3
      pwm.duty_cycle = 0
      pwm.enable()
      return pwm
    try:
      self._LEDs = [GPIO(86, "out"),
                    GPIO(77,"out"),
                    initPWM(0),
                    GPIO(140, "out"),
                    GPIO(73,"out"),
]
      self._buttons = [GPIO(141, "in"),
                       GPIO(8, "in"),
                       GPIO(7, "in"),
                       GPIO(138, "in"),
                       GPIO(6, "in"),
]
    except GPIOError as e:
      print("Unable to access GPIO pins. Did you run with sudo ?")
      sys.exit(1)

    super(UI_EdgeTpuDevBoard, self).__init__()

  def __del__(self):
    if hasattr(self, "_LEDs"):
      for x in self._LEDs or [] + self._buttons or []: x.close()

  def setLED(self, index, state):
    """Abstracts away mix of GPIO and PWM LEDs."""
    if type(self._LEDs[index]) is GPIO: self._LEDs[index].write(not state)
    else: self._LEDs[index].duty_cycle = 0.0 if state else 1.0

  def getButtonState(self):
    return [button.read() for button in self._buttons]


class TeachableMachine(object):

  def servoRun(self, flag):
      # print("Thread started.")
    while True:
      for angle in range(0, 180, 5):  # 0 - 180 degrees, 5 degrees at a time.
           #print(flag.isSet())
        flag.wait()
      # my_servo1.angle = angle
      # my_servo2.angle = angle
        self._ui.my_servo3.angle = angle
        time.sleep(0.05)
          # print("Thread running.")
      for angle in range(180, 0, -5): # 180 - 0 degrees, 5 degrees at a time.
          # print(flag.isSet())
        flag.wait()
      # my_servo1.angle = angle
      # my_servo2.angle = angle
        self._ui.my_servo3.angle = angle

        time.sleep(0.05)
          # print(flag.isSet())



  def __init__(self, model_path, ui, kNN=3, buffer_length=4):
    assert os.path.isfile(model_path), 'Model file %s not found'%model_path
    self._engine = kNNEmbeddingEngine(model_path, kNN)
    self._ui = ui
    self._buffer = deque(maxlen = buffer_length)
    self._kNN = kNN
    self._start_time = time.time()
    self._frame_times = deque(maxlen=40)
    self._servoFlag = threading.Event()
    self._servo = threading.Thread(target=self.servoRun, args=tuple([self._servoFlag]), daemon=True)
    self._servo.start()



  def classify(self, img, svg):
    # Classify current image and determine
    emb = self._engine.DetectWithImage(img)
    self._buffer.append(self._engine.kNNEmbedding(emb))
    classification = Counter(self._buffer).most_common(1)[0][0]

    # Interpret user button presses (if any)
    debounced_buttons = self._ui.getButtonState()
    n = 3
    servoRunning = False
    for i, b in enumerate(debounced_buttons):
      if not b:
        # when n isn't pressed and is recognized, continue actuating
        if i == n and classification == n:
          servoRunning = True
        elif classification != n:
          servoRunning = False
        continue
      # when n is pressed stop actuating
      if i == 0: self._engine.clear() # Hitting button 0 resets
      else : self._engine.addEmbedding(emb, i) # otherwise the button # is the class
      servoRunning = False # don't run servo during training
    self._frame_times.append(time.time())
    if servoRunning:
      self._servoFlag.set()
        #print("Thread resumed?")
    else:
      self._servoFlag.clear()
        #print("Thread stopped?")
    fps = len(self._frame_times)/float(self._frame_times[-1] - self._frame_times[0] + 0.001)

    # Print/Display results
    self._ui.setOnlyLED(classification)



    classes = ['--', 'One', 'Two', 'Three', 'Four']
    status = 'fps %.1f; #examples: %d; Class % 7s'%(
            fps, self._engine.exampleCount(),
            classes[classification or 0])
    print(status)
    svg.add(svg.text(status, insert=(26, 26), fill='black', font_size='20'))
    svg.add(svg.text(status, insert=(25, 25), fill='white', font_size='20'))


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='File path of Tflite model.',
                        default='mobilenet_quant_v1_224_headless_edgetpu.tflite')
    parser.add_argument('--testui', dest='testui', action='store_true',
                        help='Run test of UI. Ctrl-C to abort.')
    parser.add_argument('--keyboard', dest='keyboard', action='store_true',
                        help='Run test of UI. Ctrl-C to abort.')
    args = parser.parse_args()

    # The UI differs a little depending on the system because the GPIOs
    # are a little bit different.
    print('Initialize UI.')
    platform = detectPlatform()
    if args.keyboard:
      ui = UI_Keyboard()
    else:
      if platform == 'raspberry': ui = UI_Raspberry()
      elif platform == 'devboard': ui = UI_EdgeTpuDevBoard()
      else:
        print('No GPIOs detected - falling back to Keyboard input')
        ui = UI_Keyboard()

    ui.wiggleLEDs()
    if args.testui:
        ui.testButtons()
        return

    print('Initialize Model...')
    teachable = TeachableMachine(args.model, ui)

    print('Start Pipeline.')
    result = gstreamer.run_pipeline(teachable.classify)

    ui.wiggleLEDs(4)
    teachable._servoFlag.set()
    time.sleep(1)
    teachable._servoFlag.clear()




if __name__ == '__main__':
    sys.exit(main(sys.argv))


