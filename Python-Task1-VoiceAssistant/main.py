from assistant import listen, prepare_microphone, speak
from commands import AssistantExit, handle_command, is_exit_command


def main():

    if not prepare_microphone():
        return

    speak("Hello. I am your voice assistant. How can I help you?")

    while True:

        command = listen()

        if command is None:
            speak("I did not catch that. Please speak clearly and try again.")
            continue

        if not command:
            continue

        if is_exit_command(command):
            response = handle_command(command)
            speak(response)
            break

        try:
            response = handle_command(command)
        except AssistantExit:
            speak("Goodbye. Have a great day.")
            break
        except Exception as error:
            print(f"Command error: {error}")
            response = "Sorry, something went wrong while handling that request. Please try again."

        if response:
            speak(response)


if __name__ == "__main__":
    main()
