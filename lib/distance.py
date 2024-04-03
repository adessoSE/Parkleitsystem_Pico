from sensor import Sensor
from time import ticks_us, sleep_us

class CalcDistance():

    def distance(self, sensor):
        
        counter = 0
           
        sensor.trigger().on()
        sleep_us(5)
        sensor.trigger().off()
                
        while sensor.echo().value() == 0:
            tStart = ticks_us()
            counter += 1
            if counter > 100000:
                return -1
        
        counter = 0
                    
        while sensor.echo().value() == 1:
            tStop = ticks_us()
            counter += 1
            if counter > 100000:
                return -1
               
        timeElapsed = tStop - tStart
        distance = (timeElapsed * 0.03432) / 2
        return distance
