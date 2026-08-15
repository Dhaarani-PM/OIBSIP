"""Newline-delimited JSON protocol helpers shared by server and client."""

import json
import socket


def send_json(sock: socket.socket, payload: dict, lock=None) -> None:
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    if lock:
        with lock:
            sock.sendall(data)
    else:
        sock.sendall(data)


def decode_messages(buffer: str) -> tuple[list[dict], str]:
    """Extract valid JSON objects; invalid lines become error payloads."""
    messages = []
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError
            messages.append(value)
        except (json.JSONDecodeError, ValueError):
            messages.append({"type": "invalid"})
    return messages, buffer
