import speech_recognition as sr
import pyttsx3
import time
import threading


speech_lock = threading.Lock()


recognizer = sr.Recognizer()
recognizer.energy_threshold = 250
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 1.3
recognizer.non_speaking_duration = 0.6
recognizer.dynamic_energy_adjustment_damping = 0.15
recognizer.dynamic_energy_ratio = 1.5
recognizer.operation_timeout = 15


def prepare_microphone():
    try:
        with sr.Microphone() as source:
            print("Adjusting for background noise. Please stay quiet for a moment...")
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
        return True
    except (AttributeError, OSError) as error:
        print(f"Microphone setup error: {error}")
        print("Make sure PyAudio is installed and Windows has microphone access enabled.")
        return False


def speak(text):
    print(f"Assistant: {text}")

    with speech_lock:
        try:
            speech_engine = pyttsx3.init()
            speech_engine.setProperty("rate", 210)
            speech_engine.setProperty("volume", 1.0)
            speech_engine.say(text)
            speech_engine.runAndWait()
            speech_engine.stop()
        except Exception as error:
            print(f"Speech engine error: {error}")

    time.sleep(0.25)


def listen():
    try:
        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            except sr.WaitTimeoutError:
                print("No speech detected.")
                return ""
    except (AttributeError, OSError) as error:
        print(f"Microphone error: {error}")
        print("Check that a microphone is connected, selected as the Windows input device, and PyAudio is installed.")
        return ""

    try:
        print("Recognizing...")

        text = recognizer.recognize_google(audio, language="en-IN")

        print(f"You said: {text}")

        return text.lower().strip()

    except sr.UnknownValueError:
        print("Speech not understood.")
        return None

    except sr.RequestError as error:
        print(f"Speech recognition connection error: {error}")
        print("Check your internet connection and DNS, then try again.")
        return ""
