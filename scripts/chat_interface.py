import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import queue
from datetime import datetime
import os

class ChatInterface:
    def __init__(self, config=None):
        self.message_queue = queue.Queue()
        self.root = None
        self.chat_display = None
        self.config = config or {}
        
    def start_interface(self):
        """Start the chat interface in a separate thread"""
        def run_interface():
            self._create_gui()
            self._process_messages()
            self.root.mainloop()
        
        interface_thread = threading.Thread(target=run_interface, daemon=True)
        interface_thread.start()
    
    def _create_gui(self):
        """Create the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Mobile App Agent Chat")
        
        # Set window size (width x height)
        window_width = 400
        window_height = 600
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position for bottom right corner
        # Leave some margin from the edges (20 pixels)
        margin = 40
        x_position = screen_width - window_width - margin
        y_position = screen_height - window_height - margin - 40  # Extra margin for taskbar
        
        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Make window stay on top and prevent it from being minimized
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)  # Slight transparency (optional)
        
        # Prevent window from being resizable (optional)
        self.root.resizable(False, False)
        
        self.root.configure(bg='#f0f0f0')
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title
        title_label = ttk.Label(main_frame, text="Agent Chat", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 5))
        
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Arial", 9),
            bg='white',
            fg='black',
            padx=8,
            pady=8,
            height=30,
            width=45
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for alignment
        self.chat_display.tag_configure("system", 
                                       foreground="#0066CC", 
                                       font=("Arial", 12),
                                       justify=tk.LEFT)
        self.chat_display.tag_configure("human", 
                                       foreground="#8A2BE2", 
                                       font=("Arial", 12, "bold"),
                                       justify=tk.RIGHT)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(3, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", 
                                     font=("Arial", 8),
                                     foreground="#666666")
        self.status_label.pack(side=tk.LEFT)
        
        # Close button (optional)
        close_btn = ttk.Button(status_frame, text="×", width=3,
                              command=self._minimize_window)
        close_btn.pack(side=tk.RIGHT)
    
    def _minimize_window(self):
        """Minimize window instead of closing"""
        self.root.iconify()
    
    def _process_messages(self):
        """Process messages from the queue"""
        def process():
            while True:
                try:
                    if not self.message_queue.empty():
                        message = self.message_queue.get_nowait()
                        self._add_message_to_display(message)
                    self.root.after(100, process)  # Check again in 100ms
                    break
                except:
                    break
        
        self.root.after(100, process)
    
    def _add_message_to_display(self, message):
        """Add a message to the chat display"""
        if not self.chat_display:
            return
        
        msg_type = message.get("type", "system")
        content = message.get("content", "")
        is_show_message = message.get("is_show_message", False)
        
        # Only show messages that came from logger.show() OR human messages
        if not is_show_message and msg_type != "human":
            return
            
        self.chat_display.config(state=tk.NORMAL)
        
        # Add message based on type (no timestamp)
        if msg_type == "human":
            # Human messages - right aligned - remove any prefixes
            clean_content = content.replace("Task: ", "").replace("Answer: ", "")
            self.chat_display.insert(tk.END, f"You: {clean_content}\n\n", "human")
        else:
            # All other messages are system messages (left aligned)
            self.chat_display.insert(tk.END, f"{content}\n\n", "system")
        
        # Auto-scroll to bottom
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # Update status
        self.status_label.config(text=f"Last: {datetime.now().strftime('%H:%M:%S')}")
    
    def add_message(self, msg_type, content, metadata=None, is_show_message=False):
        """Add a message to the queue for display"""
        message = {
            "type": msg_type,
            "content": content,
            "metadata": metadata or {},
            "is_show_message": is_show_message
        }
        self.message_queue.put(message)
    
    def close(self):
        """Close the chat interface"""
        if self.root:
            self.root.quit()
            self.root.destroy()

# Global chat interface instance
chat_interface = None

def initialize_chat_interface(config=None):
    """Initialize the global chat interface"""
    global chat_interface
    if chat_interface is None:
        chat_interface = ChatInterface(config)
        chat_interface.start_interface()
        # Give it a moment to initialize
        import time
        time.sleep(0.5)
    return chat_interface

def add_chat_message(msg_type, content, metadata=None, is_show_message=False):
    """Add a message to the chat interface"""
    global chat_interface
    if chat_interface:
        chat_interface.add_message(msg_type, content, metadata, is_show_message)

def close_chat_interface():
    """Close the chat interface"""
    global chat_interface
    if chat_interface:
        chat_interface.close()
        chat_interface = None