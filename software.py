import usocket as socket
import urequests as request
import network
import time
import _thread
import ujson
import config
from machine import Pin
from sensor import Sensor
from distance import CalcDistance

calcDistance = CalcDistance()

sensor = Sensor(config.trigger, config.echo)

led = Pin("LED", Pin.OUT)

green = Pin(config.green, Pin.OUT)
red = Pin(config.red, Pin.OUT)
yellow = Pin(config.yellow, Pin.OUT)

sensorEmpty = True
dirty = False
lastMiddleDistance = calcDistance.distance(sensor)

picoId = 0


#IPs vom Software-IOT-Gateway und der Softwarerepräsentation
gateway = ""
software = ""


#Ports vom Software-IOT-Gateway und der Softwarerepräsentation
gateway_port = str(config.software_iot_gateway)
software_port = str(config.software_pico)


# WiFi-Konfiguration
ssid = config.ssid
password = config.password
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)


# Funktion zum setzen der LEDs
def setLed(color):
    global sensorEmpty    
    if "red" in color.lower():
        sensorEmpty = False
        red.value(1)
        yellow.value(0)
        green.value(0)
    elif "yellow" in color.lower():
        red.value(0)
        yellow.value(1)
        green.value(0)
    elif "green" in color.lower():
        sensorEmpty = True
        red.value(0)
        yellow.value(0)
        green.value(1)
    else:
        print("Color")

# Funktion für die Registrierung der Software-Repräsentation    
def handle_register_request(client_socket, addr):
    global software
    ip = str(addr).split(",")[0]
    ip = ip.split("'")[1]
    software = ip
    print("Software-IP: " + ip)
    client_socket.write("HTTP/1.1 200 OK")
    
    
# Funktion zum Verarbeiten der Anfragen zur Laufzeit
def handle_request(client_socket, addr):
    global software
    # Anfragezeile lesen
    request_line = client_socket.readline().decode("utf-8").strip()
    print("Received request:", request_line)

    # Anfrage-Header lesen
    headers = {}
    while True:
        header_line = client_socket.readline().decode("utf-8").strip()
        if not header_line:
            break
        key, value = header_line.split(":", 1)
        headers[key.strip()] = value.strip()

    # Anfrage-Methode und Pfad extrahieren
    method, path, _ = request_line.split(" ")
    print("Method:", method)
    print("Path:", path)

    # messageTypes verabreiten
    if method == "POST" and path == "/pico":
        content_length = int(headers.get("Content-Length", 0))
        body = client_socket.read(content_length).decode("utf-8")
        print("Received body:", body)
        body_json = ujson.loads(body)
        if body_json["messageType"] == "bind":
            software = addr[0]
        elif body_json["messageType"] == "setLed":
            setLed(body_json["status"])
        elif body_json["messageType"] == "heartbeat":
            request.post("http://" + software + ":" + software_port +"/software-pico", headers={"content-type":"application/json"}, data = '{"messageType":"heartbeat","important":' + str(body_json["important"]) +'}')
        
    else:
        print("Unsupported request")


#Funktion zum empfangen und setzen der Parkplatznummer
def handle_parking_id_setup(client_socket, addr):
    # Anfragezeile lesen
    request_line = client_socket.readline().decode("utf-8").strip()
    print("Received request:", request_line)

    # Anfrage-Header lesen
    headers = {}
    while True:
        header_line = client_socket.readline().decode("utf-8").strip()
        if not header_line:
            break
        key, value = header_line.split(":", 1)
        headers[key.strip()] = value.strip()

    # Anfrage-Methode und Pfad extrahieren
    method, path, _ = request_line.split(" ")
    print("Method:", method)
    print("Path:", path)
    
    if method == "POST" and path == "/setParkingId":
        content_length = int(headers.get("Content-Length", 0))
        body = client_socket.read(content_length).decode("utf-8")
        picoId = ujson.loads(body)["id"]
      
      
# Funktion zum berechnen der Distanz und senden von Veränderungen
def distance_thread():
    global lastMiddleDistance
    global dirty
    global sensorEmpty
    while True:
        distances = []
        for second in range(10):
            distance = int(calcDistance.distance(sensor))
            if distance == -1:
                dirty = True
                break
            distances.append(distance)
            time.sleep(1)
        if len(distances) != 10:
            request.post("http://" + software + ":" + software_port + "/software-pico", headers={"content-type":"application/json"}, data = '{"messageType":"sensor_info","status":"DEFECT"}')
            break
        distances.sort()
        if distances[4] < (lastMiddleDistance - 3) or distances[4] > (lastMiddleDistance + 3):
            lastMiddleDistance = distances[4]
            if sensorEmpty:
                print("Send: FREE")
                request.post("http://" + software + ":" + software_port + "/software-pico", headers={"content-type":"application/json"}, data = '{"messageType":"sensor_info","sensorId":0,"status":"FREE"}')
            else:
                print("Send: BLOCKED")
                request.post("http://" + software + ":" + software_port + "/software-pico", headers={"content-type":"application/json"}, data = '{"messageType":"sensor_info","sensorId":0,"status":"BLOCKED"}')


# WiFi-Verbindung herstellen
while not wifi.isconnected():
    pass

print("WiFi verbunden. IP-Adresse:", wifi.ifconfig()[0])


# UDP-Socket für Broadcasts
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(("0.0.0.0", config.broadcast_socket))
sock.settimeout(0.2)
message = b'' + '{"ip":"' + wifi.ifconfig()[0] + '"}'


# Broadcast zum Abfragen der IP vom IOT-Gateway
while True:
    led.value(1)
    sock.sendto(message, ("255.255.255.255", config.iot_gateway))
    time.sleep(1)
    led.value(0)
    try:
        data, addr = sock.recvfrom(1024)
    except:
        print("Can't reach IOT-Gateway")
    else:
        if data != None:
            gateway = ujson.loads(str(data).split("'")[1])["ip"]
            print("IOT-Gateway IP: " + gateway)
            break
    time.sleep(2)
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(2)
sock.close()
led.value(1)
time.sleep(1)


# HTTP-Server starten
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((wifi.ifconfig()[0], config.http_socket))
server.listen(1)


# Setzen der Parkplatznummer
client, addr = server.accept()
print("Verbindung von:", addr)
handle_parking_id_setup(client, addr)
client.send(b'HTTP/1.1 200 OK\r\n\r\n')
client.close()


# Registrierung beim Software-IOT-Gateway
register_json = '{"messageType":"register_hp","uri":"' + str(picoId) + '/'  + wifi.ifconfig()[0] + '"}'
request.post("http://" + gateway + ":" + gateway_port + "/software-iot-gateway", headers = {'content-type':'application/json'}, data = register_json)


# Thread für die Distanzberechnung starten
_thread.start_new_thread(distance_thread, ())
print("HTTP-Server gestartet. Warte auf Anfragen...")


# Warten auf Anfragen zur Laufzeit
while True:
    client, addr = server.accept()
    print("Verbindung von:", addr)
    handle_request(client, addr)
    client.write("HTTP/1.1 200 OK")
    client.close()