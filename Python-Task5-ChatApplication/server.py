"""Threaded localhost chat server."""

import socket
import threading

from auth import validate_password, validate_room_name, validate_username
from config import HOST, MAX_MESSAGE_LENGTH, PORT
from database import authenticate_user, create_room, delete_room, get_history, get_room, initialize_database, list_rooms, register_user, save_message, verify_room_password
from protocol import decode_messages, send_json


class ChatServer:
    def __init__(self):
        self.clients: dict[socket.socket, dict] = {}
        self.clients_lock = threading.Lock()

    def safe_send(self, client, payload):
        try:
            send_json(client, payload, self.clients.get(client, {}).get("send_lock"))
            return True
        except OSError:
            self.disconnect(client)
            return False

    def broadcast_room(self, room, payload, exclude=None):
        with self.clients_lock:
            targets = [sock for sock, info in self.clients.items() if info.get("room") == room and sock != exclude]
        for client in targets:
            self.safe_send(client, payload)

    def broadcast_rooms(self):
        payload = {"type": "rooms", "rooms": list_rooms()}
        with self.clients_lock:
            targets = list(self.clients)
        for client in targets:
            self.safe_send(client, payload)

    def close_deleted_room_for_clients(self, room):
        """Clear all active room selections before notifying affected clients."""
        with self.clients_lock:
            targets = [sock for sock, info in self.clients.items() if info.get("room") == room]
            for sock in targets:
                self.clients[sock]["room"] = None
        for client in targets:
            self.safe_send(client, {"type": "room_deleted", "room": room})

    def disconnect(self, client):
        with self.clients_lock:
            info = self.clients.pop(client, None)
        if not info:
            return
        try:
            client.close()
        except OSError:
            pass
        if info.get("username") and info.get("room"):
            self.broadcast_room(info["room"], {"type": "system", "message": f"{info['username']} disconnected."})

    def handle(self, client):
        buffer = ""
        try:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                messages, buffer = decode_messages(buffer)
                for message in messages:
                    self.process(client, message)
        except OSError:
            pass
        finally:
            self.disconnect(client)

    def process(self, client, message):
        kind = message.get("type")
        if kind == "invalid":
            self.safe_send(client, {"type": "error", "message": "Malformed request."})
            return
        with self.clients_lock:
            info = self.clients.get(client)
        if kind in ("register", "login"):
            username = str(message.get("username", "")).strip()
            password = str(message.get("password", ""))
            error = validate_username(username) or validate_password(password)
            if error:
                self.safe_send(client, {"type": "error", "message": error})
            elif kind == "register":
                ok, text = register_user(username, password)
                self.safe_send(client, {"type": "result", "action": "register", "ok": ok, "message": text})
            elif authenticate_user(username, password):
                with self.clients_lock:
                    info["username"] = username
                self.safe_send(client, {"type": "result", "action": "login", "ok": True, "username": username, "rooms": list_rooms()})
            else:
                self.safe_send(client, {"type": "result", "action": "login", "ok": False, "message": "Invalid username or password."})
            return
        if not info or not info.get("username"):
            self.safe_send(client, {"type": "error", "message": "Please log in first."})
            return
        if kind == "create_room":
            name = str(message.get("name", "")).strip()
            is_private = bool(message.get("is_private", False))
            room_password = str(message.get("password", ""))
            error = validate_room_name(name)
            if not error and is_private and not room_password:
                error = "A private room password is required."
            ok, text = (False, error) if error else create_room(name, info["username"], room_password if is_private else None)
            self.safe_send(client, {"type": "result", "action": "create_room", "ok": ok, "message": text})
            if ok:
                self.broadcast_rooms()
        elif kind == "delete_room":
            name = str(message.get("name", "")).strip()
            ok, text = delete_room(name, info["username"])
            self.safe_send(client, {"type": "result", "action": "delete_room", "ok": ok, "message": text, "room": name})
            if ok:
                self.close_deleted_room_for_clients(name)
                self.broadcast_rooms()
        elif kind == "join_room":
            name = str(message.get("name", "")).strip()
            room = get_room(name)
            if not room:
                self.safe_send(client, {"type": "error", "message": "Room does not exist."})
                return
            if room["is_private"] and not verify_room_password(room, str(message.get("password", ""))):
                self.safe_send(client, {"type": "error", "message": "Incorrect room password."})
                return
            previous = info.get("room")
            with self.clients_lock:
                info["room"] = name
            self.safe_send(client, {"type": "history", "room": name, "messages": get_history(name)})
            if previous and previous != name:
                self.broadcast_room(previous, {"type": "system", "message": f"{info['username']} left the room."}, client)
            self.broadcast_room(name, {"type": "system", "message": f"{info['username']} joined the room."}, client)
        elif kind == "leave_room":
            room = info.get("room")
            if room:
                with self.clients_lock:
                    info["room"] = None
                self.broadcast_room(room, {"type": "system", "message": f"{info['username']} left the room."}, client)
                self.safe_send(client, {"type": "left_room"})
        elif kind == "chat":
            text = str(message.get("message", "")).strip()
            if not info.get("room"):
                self.safe_send(client, {"type": "error", "message": "Join a room before sending a message."})
            elif not get_room(info["room"]):
                with self.clients_lock:
                    info["room"] = None
                self.safe_send(client, {"type": "error", "message": "This room no longer exists."})
            elif not text:
                self.safe_send(client, {"type": "error", "message": "Message cannot be empty."})
            elif len(text) > MAX_MESSAGE_LENGTH:
                self.safe_send(client, {"type": "error", "message": f"Message is too long (maximum {MAX_MESSAGE_LENGTH} characters)."})
            else:
                timestamp = save_message(info["room"], info["username"], text)
                self.broadcast_room(info["room"], {"type": "chat", "room": info["room"], "username": info["username"], "message": text, "timestamp": timestamp})
        elif kind == "logout":
            self.disconnect(client)

    def serve(self):
        initialize_database()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen()
            print(f"Chat server started on {HOST}:{PORT}")
            print("Waiting for connections...")
            while True:
                client, _ = server.accept()
                with self.clients_lock:
                    self.clients[client] = {"username": None, "room": None, "send_lock": threading.Lock()}
                threading.Thread(target=self.handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    try:
        ChatServer().serve()
    except OSError as error:
        print(f"Unable to start server: {error}")
