# Python Real-Time Chat Application

## Overview

A local, client-server real-time chat application built with Python, Tkinter, sockets, threading, SQLite, and JSON. It is an educational desktop project that supports multiple users and chat rooms on one computer.

## Features

- Real-time bidirectional, timestamped chat over localhost sockets
- Tkinter login, registration, and main chat interface
- Password hashing with PBKDF2-HMAC-SHA256; plaintext passwords are never stored
- Multiple named rooms, room creation, joining, and switching
- Public and password-protected rooms with visual lock indicators
- SQLite-backed users, rooms, and recent message history (latest 100 messages per room)
- Graceful client/server disconnect handling
- Modern emoji shortcodes in displayed messages (`:rofl:`, `:party:`, `:thinking:`, `:rocket:`, and more)
- In-app notification/status message and bell for messages received while the window is unfocused
- Structured newline-delimited JSON protocol with malformed-request handling

## Technologies Used

Python 3, Tkinter, `socket`, `threading`, SQLite, JSON, `hashlib`, `datetime`, and `queue`. No third-party packages are required.

## Project Structure

```text
Chat-Application/
├── auth.py          # Validation and password hashing
├── client.py        # Tkinter desktop client
├── config.py        # Local host, port, database settings
├── database.py      # SQLite schema and persistence operations
├── protocol.py      # JSON socket message helpers
├── server.py        # Threaded chat server
├── requirements.txt
├── .gitignore
└── data/            # chat.db is created automatically (ignored by Git)
```

## Installation

```powershell
git clone <repository-url>
cd Python-Task5-ChatApplication
python -m pip install -r requirements.txt
```

`requirements.txt` documents that this project only uses the Python standard library. Python 3.10 or newer is recommended.

## Running the Server

In one terminal:

```powershell
python server.py
```

The server creates `data/chat.db`, creates the default **General** room, and listens on `127.0.0.1:5050`. Change `HOST` or `PORT` in `config.py` if needed.

## Running Clients

Open a new terminal for each client:

```powershell
python client.py
```

Register accounts through the GUI, log in, select **General**, and chat. Run two client windows with different accounts to test real-time messaging.

## How It Works

Authentication requests are handled by the server, which validates usernames and hashes passwords before saving them. Rooms are created and synchronized by the server. When a client joins a room, the server returns the latest 100 room messages in chronological order. New messages are stored in SQLite using the original text, then broadcast only to users currently in that room. Emoji shortcodes are converted for display in the client, so the original shortcode text is retained in the database.

### Room Privacy

Rooms can be created as **public** (no password) or **private** (password protected). The room list displays `🔓` for public rooms and `🔒` for private rooms. Private room passwords are hashed before storage and never sent back to clients. The server checks the supplied password before adding a client to a private room or sending its history; the client UI is only a convenience layer, not the access control mechanism.

## Database

The database is automatically created at `data/chat.db` on first server startup.

- `users`: username, PBKDF2 password hash, and creation timestamp
- `rooms`: unique room names, privacy state, private-room password hashes, and creation timestamps
- `messages`: room, sender, original message, and timestamp

The generated database is intentionally ignored by Git.

## Security / Privacy

User passwords and private-room passwords are hashed rather than stored as plaintext. Chat messages are stored in the server's SQLite database. Messages are **not** end-to-end encrypted, and socket communication is **not** encrypted by default. This is an educational, localhost-oriented project, not a secure production messaging service. Do not send sensitive or private information through it.

## Limitations

- Intended for local/educational use; no TLS or cloud deployment
- SQLite is suitable for this small project, not high-scale production chat
- Notifications use a Tkinter in-app fallback (status/bell), not operating-system toast notifications
- No file sharing, typing indicators, read receipts, or voice/video calls

## Future Improvements

TLS encryption, cloud deployment, native notifications, file sharing, reactions, read receipts, and typing indicators.

## Author

Dhaarani P M
