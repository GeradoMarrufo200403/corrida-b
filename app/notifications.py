from typing import Protocol


class NotificationSender(Protocol):
    def send(self, email: str, message: str) -> None: ...


class ConsoleNotificationSender:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, email: str, message: str) -> None:
        print(f"[EMAIL a {email}]: {message}")
        self.sent.append({"email": email, "message": message})
