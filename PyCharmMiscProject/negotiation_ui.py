# negotiation_ui.py
import tkinter as tk
from tkinter import scrolledtext, Label, Button, Frame, Entry
from agent import NegotiationAgent
import threading
from speech_utils import SpeechUtils


class NegotiationUI:
    def __init__(self, parent):
        self.parent = parent
        self.agent = NegotiationAgent()
        self.deal_completed = False

        # Initialize speech utils
        self.speech_utils = SpeechUtils()

        # Create the UI
        self.create_widgets()

    def create_widgets(self):
        # Main frame for negotiation UI
        self.main_frame = Frame(self.parent, bg="#f0f0f0")

        # Back button
        self.back_button = Button(self.main_frame,
                                  text="← Back to Main Menu",
                                  bg="#607D8B", fg="white",
                                  font=("Arial", 10))
        self.back_button.pack(anchor=tk.NW, pady=(0, 10))

        # Negotiation title
        self.title = Label(self.main_frame,
                           text="Market Negotiation Assistant",
                           font=("Arial", 14, "bold"),
                           bg="#f0f0f0")
        self.title.pack(pady=(0, 20))

        # Chat history
        self.chat_frame = Frame(self.main_frame, bg="#f0f0f0")
        self.chat_history = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD,
                                                      width=70, height=20,
                                                      font=("Arial", 11))
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_history.config(state=tk.DISABLED)

        # Input area
        self.input_frame = Frame(self.main_frame, bg="#f0f0f0")
        self.input_label = Label(self.input_frame, text="Enter your message:",
                                 bg="#f0f0f0", font=("Arial", 11))
        self.input_label.pack(side=tk.LEFT, padx=10)
        self.input_text = Entry(self.input_frame, width=50, font=("Arial", 11))
        self.input_text.bind("<Return>", self.process_input)
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Voice input button
        self.voice_button = Button(self.input_frame, text="🎤 Voice",
                                   command=self.toggle_voice_input,
                                   bg="#2196F3", fg="white",
                                   font=("Arial", 11, "bold"))
        self.voice_button.pack(side=tk.RIGHT, padx=5)

        # Send button
        self.send_button = Button(self.input_frame, text="Send",
                                  command=self.process_input,
                                  bg="#4CAF50", fg="white",
                                  font=("Arial", 11, "bold"))
        self.send_button.pack(side=tk.RIGHT, padx=10)

        # Setup screen
        self.setup_frame = Frame(self.main_frame, bg="#f0f0f0")
        self.setup_label = Label(self.setup_frame,
                                 text="Describe who you're negotiating with, what for, and your maximum price:",
                                 bg="#f0f0f0", font=("Arial", 11, "bold"),
                                 wraplength=600, justify="left")
        self.setup_label.pack(pady=(50, 20))
        self.setup_entry = Entry(self.setup_frame, width=70, font=("Arial", 11))
        self.setup_entry.bind("<Return>", self.start_negotiation)
        self.setup_entry.pack(pady=10, ipady=5)

        # Setup buttons frame
        self.setup_buttons_frame = Frame(self.setup_frame, bg="#f0f0f0")
        self.setup_buttons_frame.pack(pady=10)

        # Voice setup button
        self.setup_voice_button = Button(self.setup_buttons_frame, text="🎤 Voice Input",
                                         command=self.voice_setup,
                                         bg="#673AB7", fg="white",
                                         font=("Arial", 11, "bold"))
        self.setup_voice_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

        # Start negotiation button
        self.setup_button = Button(self.setup_buttons_frame, text="Start Negotiation",
                                   command=self.start_negotiation,
                                   bg="#2196F3", fg="white",
                                   font=("Arial", 11, "bold"))
        self.setup_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

        # Decision dialog
        self.decision_frame = Frame(self.main_frame, bg="#f0f0f0")
        self.decision_label = Label(self.decision_frame,
                                    text="Would you like to accept this price?",
                                    bg="#f0f0f0", font=("Arial", 11, "bold"))
        self.decision_label.pack(side=tk.LEFT, padx=10)
        self.accept_button = Button(self.decision_frame, text="Accept",
                                    command=lambda: self.handle_decision(True),
                                    bg="#4CAF50", fg="white",
                                    font=("Arial", 11, "bold"), width=10)
        self.accept_button.pack(side=tk.RIGHT, padx=5)
        self.reject_button = Button(self.decision_frame, text="Reject",
                                    command=lambda: self.handle_decision(False),
                                    bg="#f44336", fg="white",
                                    font=("Arial", 11, "bold"), width=10)
        self.reject_button.pack(side=tk.RIGHT, padx=5)

        # Status indicator for voice
        self.status_label = Label(self.main_frame, text="", bg="#f0f0f0", fg="#888888")
        self.status_label.pack(side=tk.BOTTOM, anchor=tk.W, padx=10, pady=5)

    def voice_setup(self):
        """Use speech recognition for setup input"""
        # Change button appearance and disable
        self.setup_voice_button.config(text="Listening...", bg="#FF5722", state=tk.DISABLED)
        self.status_label.config(text="Listening for setup information... Speak now.")

        # Start listening in a separate thread
        self.speech_utils.start_listening("en-IN", self.handle_voice_setup_result)

    def handle_voice_setup_result(self, text):
        """Handle the voice recognition result for setup"""
        if text:
            # Update entry field with recognized text
            self.setup_entry.delete(0, tk.END)
            self.setup_entry.insert(0, text)

            # Update status
            self.status_label.config(text="Voice input received.")
        else:
            self.status_label.config(text="No speech detected. Please try again.")

        # Reset button
        self.setup_voice_button.config(text="🎤 Voice Input", bg="#673AB7", state=tk.NORMAL)

    def toggle_voice_input(self):
        """Handle voice input button click during chat"""
        if self.speech_utils.is_listening:
            # Already listening, do nothing
            return

        # Get the seller type to determine language
        seller_type = self.agent.get_seller_type()

        # Use Tamil for sellers who speak Tamil, English otherwise
        language = "ta-IN" if seller_type in ["auto driver", "shop keeper"] else "en-IN"

        # Update button appearance
        self.voice_button.config(text="Listening...", bg="#FF5722", state=tk.DISABLED)
        self.status_label.config(text=f"Listening... Speak in {language.split('-')[0]}")

        # Start listening
        self.speech_utils.start_listening(language, self.handle_voice_chat_result)

    def handle_voice_chat_result(self, text):
        """Handle the voice recognition result for chat"""
        # Reset button appearance
        self.voice_button.config(text="🎤 Voice", bg="#2196F3", state=tk.NORMAL)

        if text:
            # Update input field with recognized text
            self.input_text.delete(0, tk.END)
            self.input_text.insert(0, text)

            # Process the input after a short delay
            self.parent.after(500, self.process_input)

            # Update status
            self.status_label.config(text="Voice input processed.")
        else:
            self.status_label.config(text="No speech detected. Please try again.")

    def show(self, return_callback):
        # Set up the back button callback
        self.back_button.config(command=return_callback)

        # Reset negotiation
        self.agent.reset_negotiation()
        self.deal_completed = False
        self.clear_chat_history()

        # Show main frame
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Show setup frame, hide others
        self.setup_frame.pack(fill=tk.BOTH, expand=True)
        self.chat_frame.pack_forget()
        self.input_frame.pack_forget()
        self.decision_frame.pack_forget()

        # Clear setup entry
        self.setup_entry.delete(0, tk.END)
        self.setup_entry.focus_set()

        # Reset status
        self.status_label.config(text="")

    def hide(self):
        # Hide the main frame
        self.main_frame.pack_forget()

    def clear_chat_history(self):
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state=tk.DISABLED)

    def start_negotiation(self, event=None):
        full_context = self.setup_entry.get().strip()
        if not full_context:
            return

        # Clear chat history
        self.clear_chat_history()

        # Setup negotiation
        self.agent.setup_negotiation_from_full_context(full_context)
        self.deal_completed = False

        # Hide setup frame
        self.setup_frame.pack_forget()

        # Show chat interface
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.input_frame.pack(fill=tk.X)

        # Print debug info to terminal
        print(f"Negotiation setup: {self.agent.context}")
        print(f"Maximum price: ₹{self.agent.max_price}")

        # Get seller type and initial message
        seller_type = self.agent.get_seller_type()
        initial_response = self.agent.get_starting_offer()

        # Show both English and Tamil
        self.update_chat("You", f"{initial_response['english']}\n\n{initial_response['tamil']}")

        # Speak the Tamil response
        self.speech_utils.speak_text_non_blocking(initial_response['tamil'], "ta-IN")

        # Update status
        self.status_label.config(text=f"Negotiating with {seller_type}")

        # Set focus to input field
        self.input_text.focus_set()

    def process_input(self, event=None):
        if self.deal_completed:
            self.ask_new_negotiation()
            return

        seller_input = self.input_text.get().strip()
        if not seller_input:
            return

        # Clear input field
        self.input_text.delete(0, tk.END)

        # Display seller input
        seller_type = self.agent.get_seller_type()
        self.update_chat(seller_type.capitalize(), seller_input)

        # Print debug info to terminal
        print(f"\n{seller_type.capitalize()} says: {seller_input}")

        # Generate agent response
        response = self.agent.generate_response(seller_input)

        # Check if deal was automatically completed
        if "deal_completed" in response:
            self.update_chat("You", f"{response['english']}\n\n{response['tamil']}")
            self.update_chat("System", f"Deal completed at price: ₹{response['final_price']}")
            self.deal_completed = True

            # Speak the Tamil response
            self.speech_utils.speak_text_non_blocking(response['tamil'], "ta-IN")

            # Print debug info to terminal
            print(f"Deal completed at price: ₹{response['final_price']}")

            # Update status
            self.status_label.config(text=f"Deal completed at ₹{response['final_price']}")

            self.ask_new_negotiation()
            return

        # Check if we need user decision on final price
        if "request_final_decision" in response:
            self.update_chat("System", f"{response['english']}\n\n{response['tamil']}")
            self.show_decision_dialog(response["final_price"])

            # Speak the Tamil response
            self.speech_utils.speak_text_non_blocking(response['tamil'], "ta-IN")

            # Print debug info to terminal
            print(f"Asking for decision on final price: ₹{response['final_price']}")

            # Update status
            self.status_label.config(text=f"Decision needed: Accept ₹{response['final_price']}?")

            return

        # Normal response - show both English and Tamil
        self.update_chat("You", f"{response['english']}\n\n{response['tamil']}")

        # Speak the Tamil response
        self.speech_utils.speak_text_non_blocking(response['tamil'], "ta-IN")

        # Print debug info to terminal
        print(f"Your response: {response['english']}")

    def update_chat(self, speaker, message):
        """Update the chat history with a new message"""
        self.chat_history.config(state=tk.NORMAL)

        # Add speaker name with styling
        if speaker == "You":
            self.chat_history.insert(tk.END, f"\n{speaker}:\n", "you")
        else:
            self.chat_history.insert(tk.END, f"\n{speaker}:\n", "other")

        # Add the message text
        self.chat_history.insert(tk.END, f"{message}\n")

        # Scroll to the end
        self.chat_history.see(tk.END)
        self.chat_history.config(state=tk.DISABLED)

        # Configure tags for styling
        self.chat_history.tag_configure("you", foreground="#4CAF50", font=("Arial", 11, "bold"))
        self.chat_history.tag_configure("other", foreground="#2196F3", font=("Arial", 11, "bold"))

    def show_decision_dialog(self, final_price):
        """Show decision buttons for final price acceptance"""
        self.decision_label.config(text=f"Accept final price: ₹{final_price}?")
        self.input_frame.pack_forget()
        self.decision_frame.pack(fill=tk.X, pady=10)

    def handle_decision(self, accept):
        """Handle user's decision on final price"""
        # Hide decision frame
        self.decision_frame.pack_forget()
        self.input_frame.pack(fill=tk.X)

        # Tell the agent about the decision
        response = self.agent.handle_final_decision(accept)

        # Display the result
        self.update_chat("System", f"You {'accepted' if accept else 'rejected'} the deal.")

        if "deal_completed" in response:
            self.update_chat("You", f"{response['english']}\n\n{response['tamil']}")
            self.update_chat("System", f"Deal completed at price: ₹{response['final_price']}")
            self.deal_completed = True

            # Speak the Tamil response
            self.speech_utils.speak_text_non_blocking(response['tamil'], "ta-IN")

            # Update status
            self.status_label.config(text=f"Deal {'completed' if accept else 'rejected'}")

            # Ask if user wants to start a new negotiation
            self.ask_new_negotiation()
        else:
            # Continue negotiation
            self.update_chat("You", f"{response['english']}\n\n{response['tamil']}")

            # Speak the Tamil response
            self.speech_utils.speak_text_non_blocking(response['tamil'], "ta-IN")

            # Update status
            self.status_label.config(text="Negotiation continuing...")

    def ask_new_negotiation(self):
        """Ask if the user wants to start a new negotiation"""
        # Create a new dialog frame
        new_dialog_frame = Frame(self.main_frame, bg="#f0f0f0")

        # New negotiation label
        new_dialog_label = Label(new_dialog_frame,
                                 text="Would you like to start a new negotiation?",
                                 bg="#f0f0f0", font=("Arial", 11, "bold"))
        new_dialog_label.pack(side=tk.LEFT, padx=10)

        # Yes button
        yes_button = Button(new_dialog_frame, text="Yes",
                            command=self.reset_for_new_negotiation,
                            bg="#4CAF50", fg="white",
                            font=("Arial", 11, "bold"), width=10)
        yes_button.pack(side=tk.RIGHT, padx=5)

        # No button
        no_button = Button(new_dialog_frame, text="No",
                           command=lambda: self.back_button.invoke(),
                           bg="#f44336", fg="white",
                           font=("Arial", 11, "bold"), width=10)
        no_button.pack(side=tk.RIGHT, padx=5)

        # Hide input frame and show the new dialog
        self.input_frame.pack_forget()
        self.decision_frame.pack_forget()
        new_dialog_frame.pack(fill=tk.X, pady=10)

    def reset_for_new_negotiation(self):
        """Reset UI for a new negotiation"""
        # Reset state
        self.agent.reset_negotiation()
        self.deal_completed = False

        # Clear the chat history
        self.clear_chat_history()

        # Remove all frames except the main frame
        for widget in self.main_frame.winfo_children():
            if widget != self.back_button and widget != self.title:
                widget.pack_forget()

        # Show setup frame
        self.setup_frame.pack(fill=tk.BOTH, expand=True)

        # Clear setup entry
        self.setup_entry.delete(0, tk.END)
        self.setup_entry.focus_set()

        # Reset status
        self.status_label.pack(side=tk.BOTTOM, anchor=tk.W, padx=10, pady=5)
        self.status_label.config(text="")