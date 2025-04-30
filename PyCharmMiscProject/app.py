# app.py
import tkinter as tk
from tkinter import Label, Button, Frame
from negotiation_ui import NegotiationUI
from travel_ui import TravelUI


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Travel & Negotiation Assistant")
        self.geometry("900x700")
        self.configure(bg="#f0f0f0")

        # Create container for all frames
        self.container = Frame(self, bg="#f0f0f0")
        self.container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create UIs but don't show them yet
        self.negotiation_ui = NegotiationUI(self.container)
        self.travel_ui = TravelUI(self.container)

        # Create the mode selector
        self.create_mode_selector()

        # Status bar at the bottom
        self.status_bar = Label(self, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Show the mode selector first
        self.show_mode_selector()

    def create_mode_selector(self):
        # Mode selection frame
        self.mode_frame = Frame(self.container, bg="#f0f0f0")

        # Title
        title_label = Label(self.mode_frame,
                            text="Welcome to Travel & Negotiation Assistant",
                            font=("Arial", 16, "bold"),
                            bg="#f0f0f0")
        title_label.pack(pady=(50, 30))

        # Mode selection buttons
        self.travel_button = Button(self.mode_frame,
                                    text="Travel Booking",
                                    command=self.show_travel_mode,
                                    bg="#2196F3", fg="white",
                                    font=("Arial", 14, "bold"),
                                    width=20, height=2)
        self.travel_button.pack(pady=20)

        self.negotiation_button = Button(self.mode_frame,
                                         text="Market Negotiation",
                                         command=self.show_negotiation_mode,
                                         bg="#4CAF50", fg="white",
                                         font=("Arial", 14, "bold"),
                                         width=20, height=2)
        self.negotiation_button.pack(pady=20)

    def show_mode_selector(self):
        # Hide all frames
        self.negotiation_ui.hide()
        self.travel_ui.hide()

        # Show mode selector
        self.mode_frame.pack(fill=tk.BOTH, expand=True)
        self.update_status("Select a mode to continue")

    def show_negotiation_mode(self):
        # Hide mode selector
        self.mode_frame.pack_forget()

        # Show negotiation UI
        self.negotiation_ui.show(self.return_to_main)
        self.update_status("Negotiation mode activated")

    def show_travel_mode(self):
        # Hide mode selector
        self.mode_frame.pack_forget()

        # Show travel UI
        self.travel_ui.show(self.return_to_main)
        self.update_status("Travel booking mode activated")

    def return_to_main(self):
        self.show_mode_selector()

    def update_status(self, message):
        self.status_bar.config(text=message)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()