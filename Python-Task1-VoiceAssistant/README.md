# Python Voice Assistant

A Python-based voice assistant that listens to spoken commands and gives helpful spoken responses. It can handle everyday tasks such as checking the time and weather, searching the web, setting reminders, sending emails, and answering general questions.

## Features

### Core Features

- Captures voice input through the microphone using `SpeechRecognition`
- Responds to greetings such as "hello", "hi", and "hey"
- Reads out the current date and time
- Opens a Google search for a spoken topic
- Gives text-to-speech feedback using `pyttsx3`
- Asks the user to repeat when speech cannot be understood
- Supports natural exit commands such as "goodbye", "bye", and "stop"

### Advanced Features

- Understands common free-form requests for weather, time, reminders, email, and web searches
- Fetches live weather information from the OpenWeatherMap API
- Sends email through Gmail SMTP using an App Password
- Sets audible reminders for seconds, minutes, or hours
- Answers common general-knowledge questions from a local knowledge base
- Uses Gemini as a conversational fallback when a Gemini API key is configured
- Lets users update custom commands in `config.py`
- Supports time requests for selected cities, including Chennai, Mumbai, Delhi, London, Dubai, Tokyo, Singapore, Sydney, New York, and Los Angeles

## Technologies Used

- Python
- SpeechRecognition
- PyAudio
- pyttsx3
- datetime
- webbrowser
- requests
- OpenWeatherMap API
- smtplib
- python-dotenv
- Google Gen AI SDK

## Project Structure

```text
Python-Task1-VoiceAssistant/
|-- .gitignore
|-- main.py
|-- assistant.py
|-- commands.py
|-- weather.py
|-- gemini_chat.py
|-- config.py
|-- requirements.txt
`-- README.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/Dhaarani-PM/OIBSIP.git
```

Open the voice assistant project folder:

```bash
cd OIBSIP/Python-Task1-VoiceAssistant
```

Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project folder and add the keys you want to use:

```env
OPENWEATHER_API_KEY=your_openweathermap_api_key
EMAIL_ADDRESS=your_test_gmail_address@gmail.com
EMAIL_PASSWORD=your_16_character_gmail_app_password
GEMINI_API_KEY=your_gemini_api_key
```

`OPENWEATHER_API_KEY` is required for weather updates. `EMAIL_ADDRESS` and `EMAIL_PASSWORD` are required for email. Use a Gmail App Password rather than your normal Gmail password. `GEMINI_API_KEY` is optional and enables conversational fallback responses.

## Run the Application

```bash
python main.py
```

Allow microphone access in Windows when prompted.

## Voice Commands

Try commands such as:

- `Hello`
- `What time is it?`
- `What is the time in London?`
- `What is today's date?`
- `Weather in Chennai`
- `Search Python voice assistant projects`
- `Open YouTube`
- `Open Google`
- `Remind me in 10 minutes`
- `Send email`
- `What is artificial intelligence?`
- `Who are you?`
- `Goodbye`

## Custom Commands

Custom responses are stored in `config.py`. Add or edit entries in `CUSTOM_COMMANDS` to personalise the assistant.

```python
CUSTOM_COMMANDS = {
    "open youtube": "Opening YouTube.",
    "open google": "Opening Google.",
}
```

## Privacy Considerations

The assistant processes microphone audio while it is listening for a command. Speech recognition is performed through Google's speech-recognition service, so audio is sent to that service when recognising speech. Weather requests send the requested city to OpenWeatherMap. Gemini fallback messages are sent to the Gemini API only when `GEMINI_API_KEY` is configured. Email addresses, subjects, and message bodies are sent to Gmail when the user confirms an email.

The project does not save voice recordings, command history, reminder history, or email contents to local files. Keep the `.env` file private because it contains API keys and email credentials. Use a test or dummy email account for development.

## Troubleshooting

| Issue | Suggested Fix |
| --- | --- |
| Microphone is not detected | Check that a microphone is connected, selected as the Windows input device, and permitted in Windows privacy settings. |
| `PyAudio` installation fails | Install a PyAudio wheel compatible with your Python version, then run the requirements command again. |
| Weather is unavailable | Confirm that `OPENWEATHER_API_KEY` is present and active in `.env`. |
| Email cannot be sent | Use a Gmail App Password and verify `EMAIL_ADDRESS` and `EMAIL_PASSWORD`. |
| Speech is not recognised | Speak clearly, reduce background noise, and wait for microphone calibration to finish. |

## Author

Dhaarani P M

Developed as part of the OASIS Infobyte Python Programming Internship.
