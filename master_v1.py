if(1):
    import RPi.GPIO as GPIO
    import time
    import paho.mqtt.client as mqtt
    import json

    # GPIO Pin Assignments
    PUL = 16  # Motor Clock
    DIR = 19  # Motor Direction
    ENA = 14  # Motor Enable

    S1 = 23  # Carrier Sensors (Active Low)
    S2 = 24
    S3 = 25
    S4 = 26

    P1 = 4   # Position Sensors (Active Low)
    P2 = 17
    P3 = 27
    P4 = 22

    #RELAY_PIN = 8  # Relay Control #not nessery in this code

    # Stepper Motor Control Constants
    STEP_DELAY = 0.0005  # Adjust step delay for speed
    STEP_COUNT = 5       # Steps per loop iteration
    REVOLUTION_STEPS = 300  # Adjust based on motor steps per revolution

    # MQTT Broker Configuration
    broker_ip = "test.mosquitto.org"
    port = 1883
    stationid="1"
    command_topic = "PTS/STATUS/"+stationid
    blower_topic = "PTS/blower"

    # GPIO Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Configure GPIOs
    for pin in [PUL, DIR, ENA]:
        GPIO.setup(pin, GPIO.OUT)

    for pin in [S1, S2, S3, S4, P1, P2, P3, P4]:
        GPIO.setup(pin, GPIO.IN)

    # Enable Motor
    GPIO.output(ENA, GPIO.LOW)

def move_motor(direction, stop_sensor, count_max, slow_extra=False): #motor control sequence
    #dir LOW ==> Left 
    #dir HIGH ==> Right
    GPIO.output(DIR, direction)
    count = 0

    while count < count_max:
        if GPIO.input(stop_sensor) == GPIO.LOW:
            count += 1
            if count == 1:
                print("First sensor trigger - Continuing rotation for 1 revolution at half speed")
                for _ in range(REVOLUTION_STEPS):  # 1 revolution
                    GPIO.output(PUL, GPIO.HIGH)
                    time.sleep(STEP_DELAY * 4)  # Half speed
                    GPIO.output(PUL, GPIO.LOW)
                    time.sleep(STEP_DELAY * 4)
                print("Returning back to sensor position at half speed")
                GPIO.output(DIR, not direction)
                while GPIO.input(stop_sensor) == GPIO.HIGH:
                    for _ in range(STEP_COUNT):
                        GPIO.output(PUL, GPIO.HIGH)
                        time.sleep(STEP_DELAY * 4)
                        GPIO.output(PUL, GPIO.LOW)
                        time.sleep(STEP_DELAY * 4)
                GPIO.output(DIR, direction)
            if count == 2 and slow_extra:
                print("Extra backward motion at even slower speed")
                GPIO.output(DIR, not direction)
                for _ in range(REVOLUTION_STEPS // 2):
                    GPIO.output(PUL, GPIO.HIGH)
                    time.sleep(STEP_DELAY * 4)
                    GPIO.output(PUL, GPIO.LOW)
                    time.sleep(STEP_DELAY * 4)
                GPIO.output(DIR, direction)
        for _ in range(STEP_COUNT):
            GPIO.output(PUL, GPIO.HIGH)
            time.sleep(STEP_DELAY)
            GPIO.output(PUL, GPIO.LOW)
            time.sleep(STEP_DELAY)

def send_capsule(client): #capsule send sequence 
    print("Send process started")

    while GPIO.input(P1) == GPIO.LOW:
        pass
    print("Capsule detected at P1")

    move_motor(GPIO.LOW, S1, 2)
    print("Capsule dropped at target position")

    while GPIO.input(P1) == GPIO.HIGH and GPIO.input(P2) == GPIO.LOW:
        pass
    print("Capsule moved to P2 position")

    move_motor(GPIO.HIGH, S2, 3, slow_extra=True)

    while GPIO.input(P3) == GPIO.LOW:
        pass
    print("Blower on ")
    client.publish(blower_topic, "b")
    print("Package sent")
    print("System reset to pass-through state")

def receive_capsule(client): ##capsule receive sequence
    print("Receive process started")

    while GPIO.input(P3) == GPIO.LOW:
        pass
    client.publish(blower_topic, "stop")

    move_motor(GPIO.LOW, S3, 3)
    print("SUCTION HIGH - Capsule Picked")
    client.publish(blower_topic, "s")

    while GPIO.input(P4) == GPIO.LOW:
        pass
    move_motor(GPIO.HIGH, S4, 3, slow_extra=True)
    client.publish(blower_topic, "stop")

    time.sleep(2)
    print("Package received")

    move_motor(GPIO.LOW, S2, 1)
    print("System reset to pass-through state")

def on_message(client, userdata, message): #message from mqtt
    command = message.payload.decode()
    

    if command == "Send":
        send_capsule(client)
    elif command == "Recieve":
        receive_capsule(client)
    else:
        pass

def main(): #main function 
    client = mqtt.Client()
    client.on_message = on_message

    client.connect(broker_ip, port, 60)
    client.subscribe(command_topic)

    print("Waiting for commands...")
    client.loop_forever()

#execution 
#no change needed 
try:
    main()
except KeyboardInterrupt:
    print("\nStopping system...")
finally:
    GPIO.output(ENA, GPIO.HIGH)  # Disable motor
    GPIO.cleanup()
