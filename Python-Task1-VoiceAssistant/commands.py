from datetime import datetime
from weather import get_weather
import webbrowser
import threading
import re
import smtplib
import os
import requests
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from email.message import EmailMessage
from dotenv import load_dotenv

from assistant import speak, listen
from config import CUSTOM_COMMANDS
from gemini_chat import get_conversational_reply



load_dotenv()


EXIT_COMMANDS = {"goodbye", "bye", "exit", "quit", "stop", "close"}


class AssistantExit(Exception):
    """Raised when the user asks to exit during a multi-step conversation."""


TIME_ZONES = {
    "london": "Europe/London",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "dubai": "Asia/Dubai",
    "tokyo": "Asia/Tokyo",
    "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney",
    "chennai": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
}


def is_exit_command(command):
    """Recognise natural goodbye phrases such as 'okay, goodbye assistant'."""
    words = set(re.findall(r"\b[a-z]+\b", command.lower()))
    return bool(words & EXIT_COMMANDS)


def extract_weather_city(command):
    """Extract a city from natural weather questions."""
    match = re.search(r"\b(?:weather|forecast).*?\s+(?:in|for|at)\s+(.+)", command)
    if match:
        city = match.group(1).strip(" ?.!")
        return re.sub(r"\s+(?:today|now|currently|right now)$", "", city)

    match = re.search(r"\b(?:in|for|at)\s+(.+?)\s+(?:weather|forecast)\b", command)
    if match:
        return match.group(1).strip(" ?.!")

    match = re.search(r"\bweather\s+(.+)", command)
    if match:
        city = match.group(1).strip(" ?.!")
        if city not in {"today", "now", "like"}:
            return city
    return ""


def get_time_response(command):
    """Return local time or a supported city's timezone-aware time."""
    for city, timezone_name in TIME_ZONES.items():
        if re.search(rf"\b{re.escape(city)}\b", command):
            try:
                current_time = datetime.now(ZoneInfo(timezone_name)).strftime("%I:%M %p")
                return f"The current time in {city.title()} is {current_time}."
            except ZoneInfoNotFoundError:
                return "Timezone data is missing. Please install the project requirements and try again."

    current_time = datetime.now().strftime("%I:%M %p")
    return f"The current time is {current_time}."




def set_reminder(seconds):

    def reminder_alert():
        speak("Reminder: Your timer is complete.")

    timer = threading.Timer(seconds, reminder_alert)
    timer.daemon = True
    timer.start()




def apply_email_spelling_correction(recipient, correction):
    """Apply corrections such as 'change Prabhu to P R A B U'."""
    match = re.search(
        r"(?:correct|change)(?:\s+the)?(?:\s+spelling)?(?:\s+of)?\s+"
        r"([a-z0-9._-]+)\s+to\s+(.+)",
        correction.lower(),
    )
    if not match:
        return None

    old_text = match.group(1)
    replacement_text = match.group(2).strip()
    individual_letters = re.findall(r"\b[a-z]\b", replacement_text)
    new_text = "".join(individual_letters) if individual_letters else replacement_text.split()[0]

    if old_text not in recipient or not new_text:
        return None

    return recipient.replace(old_text, new_text, 1)


def ask_for_email_detail(question, attempts=3):
    """Ask one email question again when speech is missed."""
    for attempt in range(attempts):
        speak(question if attempt == 0 else "I did not catch that. Please say it again.")
        answer = listen()

        if answer and is_exit_command(answer):
            raise AssistantExit

        if answer:
            return answer

    return ""


def send_email(recipient, subject, body):

    sender_email = os.getenv("EMAIL_ADDRESS")
   
    sender_password = os.getenv("EMAIL_PASSWORD", "").replace(" ", "")

    if not sender_email or not sender_password:
        return (
            "Email is not configured. "
            "Please add EMAIL_ADDRESS and EMAIL_PASSWORD to your .env file."
        )

    try:
        message = EmailMessage()

        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject

        message.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(message)

        return f"Email sent successfully to {recipient}."

    except smtplib.SMTPAuthenticationError as error:
        print("Email error:", error)
        return (
            "Gmail rejected the login. Use your Gmail address and a 16-character "
            "Google App Password in EMAIL_PASSWORD. Regular Gmail passwords do not work."
        )
    except smtplib.SMTPException as error:
        print("Email error:", error)
        return "Sorry, I could not send the email. Please check the recipient and Gmail settings."
    except OSError as error:
        print("Email connection error:", error)
        return "Sorry, I could not connect to Gmail. Please check your internet connection."


def compose_email():
    while True:
        recipient = ask_for_email_detail("Who should I send the email to?")

        if not recipient:
            return "I could not understand the recipient, so I cancelled the email."

      
        recipient = recipient.lower().strip()
        recipient = recipient.replace(" at ", "@")
        recipient = recipient.replace(" dot ", ".")
        recipient = recipient.replace(" ", "")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
            speak("That does not sound like a valid email address. Please say it again.")
            continue

       
        while True:
            confirmation = ask_for_email_detail(
                f"I understood {recipient}. Is that correct? Please say yes or no. "
                "To fix a name, say change old spelling to new spelling."
            )

            corrected_recipient = apply_email_spelling_correction(recipient, confirmation)
            if corrected_recipient:
                recipient = corrected_recipient
                speak(f"Okay, I changed it to {recipient}.")
                continue

            if confirmation and re.fullmatch(r"(?:yes|correct|right|send)", confirmation.strip()):
                break

            if confirmation and re.search(r"\b(no|wrong|change|again)\b", confirmation):
                speak("Okay, let's enter the recipient again.")
                break

            return "I did not get a clear confirmation, so I cancelled the email."

      
        if confirmation and re.search(r"\b(no|wrong|change|again)\b", confirmation):
            continue

        break

    subject = ask_for_email_detail("What should be the subject?")

    if not subject:
        return "I could not understand the subject, so I cancelled the email."

    body = ask_for_email_detail("What should I write in the email?")

    if not body:
        return "I could not understand the email message, so I cancelled the email."

    speak("Sending the email now.")

    return send_email(
        recipient,
        subject,
        body
    )



KNOWLEDGE_BASE = {

    "what is python":
        "Python is a high-level programming language known for its simple syntax and wide range of applications.",

    "what is artificial intelligence":
        "Artificial Intelligence is the field of creating computer systems that can perform tasks that normally require human intelligence.",

    "what is machine learning":
        "Machine Learning is a branch of artificial intelligence where computers learn patterns from data and use them to make predictions or decisions.",

    "what is the capital of india":
        "The capital of India is New Delhi.",

    "what is the capital of france":
        "The capital of France is Paris.",

    "what is the largest planet":
        "Jupiter is the largest planet in our solar system.",

    "what is the smallest planet":
        "Mercury is the smallest planet in our solar system.",

    "how many planets are there":
        "There are eight recognized planets in our solar system.",

    "what is the speed of light":
        "The speed of light in a vacuum is approximately 299,792 kilometers per second.",

    "who developed python":
        "Python was created by Guido van Rossum and was first released in 1991.",

    "what is the boiling point of water":
        "The boiling point of water is 100 degrees Celsius at standard atmospheric pressure.",

    "what is the largest ocean":
        "The Pacific Ocean is the largest ocean on Earth.",

    "what is the tallest mountain":
        "Mount Everest is the highest mountain above sea level.",

    "what is the full form of cpu":
        "CPU stands for Central Processing Unit.",

    "what is the full form of ram":
        "RAM stands for Random Access Memory.",

    "what is the full form of ai":
        "AI stands for Artificial Intelligence.",

    "what is the full form of ml":
        "ML stands for Machine Learning."
}


def answer_general_question(command):

    command = command.lower().strip()

    
    if command in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[command]

   
    for question, answer in KNOWLEDGE_BASE.items():

        if question in command:
            return answer

    return None


def answer_from_wikipedia(question):
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": question,
        "format": "json",
        "srlimit": 1,
    }

    try:
        search_data = requests.get(search_url, params=search_params, timeout=8).json()
        results = search_data.get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0]["title"]
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote_plus(title)
        summary_data = requests.get(summary_url, timeout=8).json()
        summary = summary_data.get("extract", "").strip()
        if not summary:
            return None

        # Spoken answers should stay short and easy to follow.
        sentences = re.split(r"(?<=[.!?])\s+", summary)
        return " ".join(sentences[:2])
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def answer_personal_question(command):
    """Handle natural small-talk and identity questions."""
    if "how are you" in command:
        return "I'm doing well, thanks for asking. How are you?"
    if "your father" in command or "who made you" in command or "who created you" in command:
        return "I do not have a father like a person does. I was built as a Python voice assistant project by my developer."
    if "your name" in command:
        return "I'm your Python voice assistant. You can give me a name if you like."
    if "thank" in command:
        return "You're welcome."
    return None


# ============================================================
# CUSTOM COMMANDS
# ============================================================

def handle_custom_command(command):

    for trigger, response in CUSTOM_COMMANDS.items():

        if trigger in command:

            if trigger == "open youtube":
                webbrowser.open("https://www.youtube.com")
                return response

            if trigger == "open google":
                webbrowser.open("https://www.google.com")
                return response

            return response

    return None


# ============================================================
# MAIN COMMAND HANDLER
# ============================================================

def handle_command(command):

    command = command.lower().strip()


    # --------------------------------------------------------
    # Greeting
    # --------------------------------------------------------

    if command in [
        "hello",
        "hi",
        "hey",
        "hello assistant",
        "hi assistant"
    ]:
        return "Hello! How can I help you?"


    # --------------------------------------------------------
    # Goodbye
    # --------------------------------------------------------

    if is_exit_command(command):
        return "Goodbye. Have a great day."


    # --------------------------------------------------------
    # Current time
    # --------------------------------------------------------

    if "time" in command or "what hour" in command:
        return get_time_response(command)


    # --------------------------------------------------------
    # Current date
    # --------------------------------------------------------

    if "date" in command or "what day is it" in command or "today's day" in command:

        current_date = datetime.now().strftime(
            "%A, %B %d, %Y"
        )

        return f"Today is {current_date}."


    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    if (
        "send email" in command
        or "send an email" in command
        or "write an email" in command
        or "compose email" in command
    ):

        return compose_email()


    # --------------------------------------------------------
    # Reminder
    # --------------------------------------------------------

    if "reminder" in command or "remind me" in command:

        match = re.search(
            r"(?:for|in)\s+(\d+)\s*"
            r"(second|seconds|minute|minutes|hour|hours)",
            command
        )

        if not match:

            return (
                "Please tell me the duration, "
                "for example, remind me in 10 seconds."
            )

        amount = int(match.group(1))
        unit = match.group(2)

        if "second" in unit:

            seconds = amount

        elif "minute" in unit:

            seconds = amount * 60

        else:

            seconds = amount * 3600

        set_reminder(seconds)

        if seconds < 60:

            return (
                f"Okay. I will remind you in "
                f"{amount} seconds."
            )

        if seconds < 3600:

            return (
                f"Okay. I will remind you in "
                f"{amount} minutes."
            )

        return (
            f"Okay. I will remind you in "
            f"{amount} hours."
        )


    # --------------------------------------------------------
    # Weather
    # --------------------------------------------------------

    if "weather" in command or "forecast" in command:

        city = extract_weather_city(command)


        if not city:

            return "Which city would you like the weather for?"


        return get_weather(city)


    # --------------------------------------------------------
    # Web search
    # --------------------------------------------------------

    search_match = re.search(r"\b(?:search(?:\s+for)?|look up|google)\s+(.+)", command)
    if search_match:

        query = search_match.group(1).strip(" ?.!")


        if query:

            search_url = (
                "https://www.google.com/search?q="
                + quote_plus(query)
            )

            webbrowser.open(search_url)

            return (
                f"Searching the web for {query}."
            )


        return "What would you like me to search for?"


    # --------------------------------------------------------
    # Custom commands
    # --------------------------------------------------------

    custom_response = handle_custom_command(command)

    if custom_response:

        return custom_response


    # --------------------------------------------------------
    # General knowledge
    # --------------------------------------------------------

    answer = answer_general_question(command)

    if answer:

        return answer

    personal_answer = answer_personal_question(command)

    if personal_answer:
        return personal_answer

    # Gemini handles natural conversation and general questions while the
    # specific actions above remain deterministic and safe.
    return get_conversational_reply(command)


    # --------------------------------------------------------
    # Unknown command
    # --------------------------------------------------------

    if "help" in command or "what can you do" in command:
        return (
            "I can answer many general questions using Wikipedia, tell time or date, "
            "check weather, search the web, set reminders, open websites, and send emails."
        )

