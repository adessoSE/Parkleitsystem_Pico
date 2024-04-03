from machine import Pin


'''
Ein Sensor speichert den eigenen trigger und echo Pin.
Über den Zugriff auf distance.py gibt die Funktion distance() die momentane Distanz aus.
'''


class Sensor:
    trigger = Pin(0, Pin.OUT)
    echo = Pin(1, Pin.IN)

    def __init__(self, triggerPin, echoPin):
        global trigger
        global echo
        
        trigger = Pin(triggerPin, Pin.OUT)
        echo = Pin(echoPin, Pin.IN)

    def trigger(self):
        return trigger

    def echo(self):
        return echo