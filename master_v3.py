if(1):

    import RPi.GPIO as GPIO

    import time

    import paho.mqtt.client as mqtt

    import json

    import threading



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



    # Stepper Motor Control Constants

    STEP_DELAY = 0.0005

    STEP_COUNT = 5

    REVOLUTION_STEPS = 150



    # MQTT Broker Configuration

    broker_ip = "test.mosquitto.org"

    port = 1883

    stationid = "2"

    command_topic = f"PTS/ACTION/{stationid}"

    blower_topic = "PTS/blower"







    # === GPIO Setup ===

    GPIO.setmode(GPIO.BCM)

    GPIO.setwarnings(False)







    for pin in [PUL, DIR, ENA]:

        GPIO.setup(pin, GPIO.OUT)







    for pin in [S1, S2, S3, S4, P1, P2, P3, P4]:

        GPIO.setup(pin, GPIO.IN)



    GPIO.output(ENA, GPIO.LOW)  # Enable Motor







    # === MQTT Client Setup ===



    client = mqtt.Client()



def on_connect(client, userdata, flags, rc):



    if rc == 0:



        print("[MQTT] Connected successfully")



        client.subscribe(command_topic)



        print(f"[MQTT] Subscribed to: {command_topic}")



    else:



        print(f"[MQTT] Connection failed with code {rc}")



def on_disconnect(client, userdata, rc):



    print(f"[MQTT] Disconnected (code {rc})")



    while rc != 0:



        print("[MQTT] Attempting to reconnect...")



        try:



            rc = client.reconnect()



        except:



            time.sleep(2)



def on_message(client, userdata, message):



    command = message.payload.decode()



    if command == "send":

        motor_thread = threading.Thread(target=send_capsule)

        motor_thread.start()



    elif command == "receive":

        motor_thread = threading.Thread(target=receive_capsule)

        motor_thread.start()



    else:



        print(f"[MQTT] Unknown command: {command}")



def publish_message(topic, message, qos=1, retain=True, max_retries=3):



    retries = 0



    while retries < max_retries:



        result = client.publish(topic, message, qos=qos, retain=retain)



        if result.rc == mqtt.MQTT_ERR_SUCCESS:



            print(f"[DEBUG] Successfully published to {topic}: {message}")



            return True



        else:



            retries += 1



            print(f"[DEBUG] Failed to publish to {topic}, attempt {retries}/{max_retries}")



            time.sleep(1)  # Wait before retrying



    print(f"[ERROR] Failed to publish to {topic} after {max_retries} attempts")



    return False



def move_motor(direction, stop_sensor, count_max, slow_extra=False):



    GPIO.output(DIR, direction)



    count = 0







    while count < count_max:



        if GPIO.input(stop_sensor) == GPIO.LOW:



            count += 1



            if count == 1:



                print("Sensor triggered - 1 revolution at half speed")



                for _ in range(REVOLUTION_STEPS):



                    GPIO.output(PUL, GPIO.HIGH)



                    time.sleep(STEP_DELAY * 4)



                    GPIO.output(PUL, GPIO.LOW)



                    time.sleep(STEP_DELAY * 4)



                print("Reversing to sensor position")



                GPIO.output(DIR, not direction)



                while GPIO.input(stop_sensor) == GPIO.HIGH:



                    for _ in range(STEP_COUNT):



                        GPIO.output(PUL, GPIO.HIGH)



                        time.sleep(STEP_DELAY * 4)



                        GPIO.output(PUL, GPIO.LOW)



                        time.sleep(STEP_DELAY * 4)



                GPIO.output(DIR, direction)



            if count == 2 and slow_extra:



                print("Extra backward motion")



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



def send_capsule():



    global client



    print("[SEND] Waiting for capsule at P1...")



    while GPIO.input(P1) == GPIO.LOW:



        pass



    print("[SEND] Capsule detected at P1")







    move_motor(GPIO.LOW, S1, 2)



    print("[SEND] Capsule dropped")







    while GPIO.input(P1) == GPIO.HIGH and GPIO.input(P2) == GPIO.LOW:



        pass



    print("[SEND] Capsule at P2")







    move_motor(GPIO.HIGH, S2, 3, slow_extra=True)







    while GPIO.input(P3) == GPIO.LOW:



        pass



    print("[SEND] Blower ON")



    if publish_message(blower_topic, "b"):



        print("[SEND] Package sent, system reset")



def receive_capsule():



    print("[RECEIVE] Waiting at P3...")



    while GPIO.input(P3) == GPIO.LOW:

        pass







    move_motor(GPIO.LOW, S3, 3)



    if publish_message("PTS/blower", "b", qos=1):  # Use the new publish function



        time.sleep(0.2)

        print("[RECEIVE] Blower SUCTION, capsule picked")



    print("[RECEIVE] Blower SUCTION, capsule picked")







    while GPIO.input(P4) == GPIO.LOW:



        pass







    if publish_message("PTS/blower", "stop", qos=1):  # Use the new publish function



        print("[RECEIVE] Blower OFF")



    



    move_motor(GPIO.HIGH, S4, 3, slow_extra=True)

    time.sleep(2)

    print("[RECEIVE] Package received")

    move_motor(GPIO.LOW, S2, 1)

    print("[RECEIVE] Reset complete")



def main():

    client.connect(broker_ip, port, 3600)

    print("[SYSTEM] Waiting for commands...")

    client.loop_forever()



# Assign MQTT callbacks



client.on_connect = on_connect

client.on_disconnect = on_disconnect

client.on_message = on_message







# === Execution ===



try:

    main()



except KeyboardInterrupt:

    print("\n[SYSTEM] Interrupted by user. Shutting down...")

finally:



    GPIO.output(ENA, GPIO.HIGH)

    GPIO.cleanup()

