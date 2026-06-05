import webbrowser
from urllib.parse import quote


class MobileController:
    def __init__(self):
        pass

    def send_whatsapp_message(self, number: str, message: str) -> str:
        """
        Uses WhatsApp Web URI scheme to open a chat and pre-fill the message.
        User still has to press Send, for security reasons.
        """
        print(f" Sending WhatsApp message to {number}...")

        # Clean number formatting (must include country code)
        clean_number = "".join(filter(str.isdigit, number))
        if len(clean_number) == 10:
            clean_number = "91" + clean_number  # Default to India (+91)
        elif len(clean_number) == 0:
            return "Invalid phone number. Please provide a valid number."

        # Properly encode the message for URL (handles &, #, ?, spaces, etc.)
        encoded_message = quote(message, safe='')
        url = f"https://wa.me/{clean_number}?text={encoded_message}"
        webbrowser.open(url)
        return f"Opening WhatsApp to send the message. Please press Send."


mobile_controller = MobileController()
