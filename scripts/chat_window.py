import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import socket
import threading
import json

HOST = "127.0.0.1"
PORT = 5055

class ChatWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        self.root.title("Mobile App Agent Chat")

        # ⬅️ Slightly wider and aligned bottom-right
        width, height = 450, 420
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - width - 40
        y = screen_height - height - 100
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg="white")

        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Arial", 12),
            padx=10,
            pady=10,
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)

        threading.Thread(target=self.start_server, daemon=True).start()
        self.root.mainloop()

    def start_server(self):
        """Simple socket listener for messages."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        while True:
            conn, _ = s.accept()
            data = conn.recv(4096)
            if not data:
                conn.close()
                continue
            try:
                msg = json.loads(data.decode())
                self.root.after(0, self.show_message, msg["text"], msg.get("sender", "system"))
            except Exception as e:
                print("Parse error:", e)
            conn.close()

    def show_message(self, message, sender="system"):
        # 🧹 Clean + format message
        message = message.replace("(Human Response):", "").strip()
        if message:
            message = message[0].upper() + message[1:]

        # 🎨 Colors
        color_map = {"system": "goldenrod", "user": "royalblue"}
        color = color_map.get(sender, "black")

        # 💬 Build message text
        if sender == "system":
            text = f"System: {message}\n"
            justify = "left"
        else:
            text = f"You: {message}\n"
            justify = "right"

        # 🔖 Insert text with isolated color + alignment
        self.text_area.configure(state=tk.NORMAL)
        start_index = self.text_area.index(tk.END)
        self.text_area.insert(tk.END, text)
        end_index = self.text_area.index(tk.END)

        unique_tag = f"{sender}_{start_index}"  # unique tag per message
        self.text_area.tag_add(unique_tag, start_index, end_index)
        self.text_area.tag_config(
            unique_tag,
            foreground=color,
            justify=justify,
            lmargin1=10,   # left margin for readability
            rmargin=10     # right margin for padding
        )

        self.text_area.configure(state=tk.DISABLED)
        self.text_area.yview(tk.END)

if __name__ == "__main__":
    ChatWindow()
