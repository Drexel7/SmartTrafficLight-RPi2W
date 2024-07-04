from flask import Flask, render_template, redirect, request, url_for
from gpiozero import LED, PWMLED, Button, Device
from gpiozero.pins.pigpio import PiGPIOFactory
import atexit
import threading
import time
import RPi.GPIO as GPIO

app = Flask(__name__)

# Configurare LED-uri GPIO
Device.pin_factory = PiGPIOFactory()
red_led = PWMLED(27)
yellow_led = PWMLED(22)
green_led = PWMLED(23)
blue_led = PWMLED(24)
buzzer = PWMLED(15)  # buzzer pasiv control prin pwmled

# Configurare servo
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(12, GPIO.OUT)
servo = GPIO.PWM(12, 50)
servo.start(0)

# Configurare butoane
start_button = Button(4)
stop_button = Button(21)

# Variabile de control
running = False
night_mode = False

# Valori implicite pentru ratele de clipire și duratele LED-urilor
flicker_rate = 0.5
red_duration = 3
green_duration = 3

# Funcție pentru curățarea resurselor
def cleanup():
    red_led.close()
    yellow_led.close()
    green_led.close()
    blue_led.close()
    buzzer.close()
    servo.stop()
    GPIO.cleanup()

atexit.register(cleanup)

# Funcție pentru intermitența LED-urilor și controlul buzzer-ului prin PWM
def flicker_led(led, rate, duration, brightness=1.0, activate_buzzer=False, buzzer_freq=440):
    start_time = time.time()
    while time.time() - start_time < duration and running:
        led.value = brightness
        if activate_buzzer:
            buzzer.frequency = buzzer_freq  # setez frecventa
            buzzer.value = 0.5  # 50 % duty cycle
        time.sleep(rate)
        led.off()
        if activate_buzzer:
            buzzer.off()
        time.sleep(rate)

# Funcție pentru mișcarea servo-ului
def move_servo(position):
    print(f"Mută servo la poziția {position}")
    servo.ChangeDutyCycle(position)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)

# Secvența de control a semaforului
def traffic_light_sequence():
    global running, flicker_rate, red_duration, green_duration, night_mode
    while True:
        if running:
            current_red_duration = red_duration / 2 if night_mode else red_duration
            current_green_duration = green_duration / 2 if night_mode else green_duration

            print(f"Night Mode: {night_mode}, Red Duration: {current_red_duration}, Green Duration: {current_green_duration}")

            brightness = 0.2 if night_mode else 1.0

            # Mută servo în poziția blocată
            move_servo(5)  
            flicker_led(red_led, flicker_rate, current_red_duration, brightness=brightness)
            yellow_led.value = brightness
            time.sleep(3)
            yellow_led.off()

            # Mută servo în poziția deschisă
            move_servo(10)
            flicker_led(green_led, flicker_rate, current_green_duration, brightness=brightness, activate_buzzer=True)

        time.sleep(0.1)

# Pornire secvență într-un thread separat
threading.Thread(target=traffic_light_sequence, daemon=True).start()

# Funcții pentru controlul traficului și modului de noapte
def start_traffic():
    global running
    running = True

def stop_traffic():
    global running
    running = False 

def turn_on_blue_led():
    blue_led.on()

def turn_off_blue_led():
    blue_led.off()

def enable_night_mode():
    global night_mode
    night_mode = True
    turn_on_blue_led()
    print("Night mode enabled")

def disable_night_mode():
    global night_mode
    night_mode = False
    turn_off_blue_led()
    print("Night mode disabled")

# Configurare evenimente pentru butoane fizice
start_button.when_pressed = start_traffic
stop_button.when_pressed = stop_traffic

# Rute pentru controlul din interfața web
@app.route('/start')
def start():
    start_traffic()
    return redirect(url_for('index'))

@app.route('/stop')
def stop():
    stop_traffic()
    return redirect(url_for('index'))

@app.route("/", methods=["GET", "POST"])
def index():
    global flicker_rate, red_duration, green_duration
    if request.method == "POST":
        print("Received POST request")
        if "start_button" in request.form:
            flicker_rate = float(request.form.get("flicker_rate", 0.5))
            red_duration = int(request.form.get("red_duration", 3))
            green_duration = int(request.form.get("green_duration", 3))
            print(f"Updated settings: flicker_rate={flicker_rate}, red_duration={red_duration}, green_duration={green_duration}")
            start_traffic()
        elif "stop_button" in request.form:
            stop_traffic()
        elif "night_mode_on" in request.form:
            enable_night_mode()
        elif "night_mode_off" in request.form:
            disable_night_mode()
        elif "servo_left_button" in request.form:
            move_servo(5)
        elif "servo_right_button" in request.form:
            move_servo(10)
        elif "servo_center_button" in request.form:
            move_servo(7.5)
    return render_template("index.html", flicker_rate=flicker_rate, red_duration=red_duration, green_duration=green_duration)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=82, debug=True)
    finally:
        cleanup()
