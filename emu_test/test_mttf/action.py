"""Contains the individual actions that can be send to the telnet console.
"""
import random
import time


class Action(object):
  """Parent class of every action that can be send to the emulator."""

  def __init__(self, interval):
    self.interval = interval

  def __lt__(self, other):
    return self.interval < other.interval


class MouseEvent(Action):
  """Sends one mouse event every 10 ms."""

  def __init__(self, width, height):
    super(MouseEvent, self).__init__(0.01)
    self.width = int(width)
    self.height = int(height)
    self.x = random.randint(0, self.width)
    self.y = random.randint(0, self.height)

  def produce_event(self):
    # This makes sure we jump to a different region on the screen
    self.x = self.x if random.random() < 0.9 else random.randint(0, self.width)
    self.y = self.y if random.random() < 0.9 else random.randint(0, self.height)

    # This keeps the movement relatively local
    self.y = min(self.height, max(0, self.y + random.randint(-5, 5)))
    self.x = min(self.width, max(0, self.x + random.randint(-5, 5)))

    # 80% chance of a mouse down.
    btn = 1 if random.random() < 0.8 else 0

    return "event mouse {0} {1} 0 {2}".format(self.x, self.y, btn)


class SmsEvent(Action):
  """Sms every 10 seconds.."""
  NAMES = [ "Falstaff", "Julius", "Marc-Anthony", "Hamlet",
      "Othello", "Iago", "Antony", "Timon", "Cleopatra",
      "Rosalind", "Brutus", "Vincentio", "Coriolanus"
  ]

  WORDLIST = [
      "a", "about", "all", "also", "and", "as", "at", "be", "because", "but",
      "by", "can", "come", "could", "day", "do", "even", "find", "first", "for",
      "from", "get", "give", "go", "have", "he", "her", "here", "him", "his",
      "how", "I", "if", "in", "into", "it", "its", "just", "know", "like",
      "look", "make", "man", "many", "me", "more", "my", "new", "no", "not",
      "now", "of", "on", "one", "only", "or", "other", "our", "out", "people",
      "say", "see", "she", "so", "some", "take", "tell", "than", "that", "the",
      "their", "them", "then", "there", "these", "they", "thing", "think",
      "this", "those", "time", "to", "two", "up", "use", "very", "want", "way",
      "we", "well", "what", "when", "which", "who", "will", "with", "would",
      "year", "you", "your"
  ]

  def __init__(self):
    super(SmsEvent, self).__init__(10)

  def produce_event(self):
    return "sms send {} {} {} {} {}".format(
        random.choice(SmsEvent.NAMES), random.choice(SmsEvent.WORDLIST),
        random.choice(SmsEvent.WORDLIST), random.choice(SmsEvent.WORDLIST),
        random.choice(SmsEvent.WORDLIST))


class GeoEvent(Action):
  """Geo every 1 second."""

  def __init__(self):
    super(GeoEvent, self).__init__(1)
    # Start wandering along the googleplex..
    self.lat = 37.422206
    self.long = -122.086088

  def produce_event(self):
    self.long = min(180, max(0, self.long + random.random() - 0.5))
    self.lat = min(90, max(-90, self.lat + random.random() - 0.5))
    return "geo fix {0} {1}".format(self.long, self.lat)


class PowerEvent(Action):
  """Power event every minute."""

  def __init__(self):
    super(PowerEvent, self).__init__(60)

  def produce_event(self):
    if random.random() > 0.9:
      ac = "on" if bool(random.getrandbits(1)) else "off"
      return "power ac {0}".format(ac)

    return "power capacity {0}".format(random.randint(0, 100))


class ScreenRecord(Action):
  """Screen record every minute."""

  def __init__(self):
    super(ScreenRecord, self).__init__(60)

  def produce_event(self):
    if random.random() > 0.5:
      return "screenrecord start a.webm"
    else:
      return "screenrecord stop"


class Finger(Action):
  """Hit the finger sensor every minute"""

  def __init__(self):
    super(Finger, self).__init__(60)

  def produce_event(self):
    if random.random() > 0.5:
      return "finger touch 1"
    else:
      return "finger remove"


class Snapshot(Action):
  """Every other minute take/load a snapshot."""

  def __init__(self):
    super(Snapshot, self).__init__(120)

  def produce_event(self):
    if random.random() > 0.5:
      return "avd snapshot save monkey"
    else:
      return "avd snapshot load monkey"


class Sensor(Action):
  """Sensor status every second."""

  def __init__(self):
    super(Sensor, self).__init__(1)
    self.sensors = [
        "acceleration", "gyroscope", "magnetic-field", "orientation",
        "temperature", "proximity", "light", "pressure", "humidity",
        "magnetic-field-uncalibrated", "gyroscope-uncalibrated"
    ]

  def produce_event(self):
    a = random.randint(0, 256)
    b = random.randint(0, 256)
    c = random.randint(0, 256)
    return "sensor set {0} {1}:{2}:{3}".format(
        random.choice(self.sensors), a, b, c)
