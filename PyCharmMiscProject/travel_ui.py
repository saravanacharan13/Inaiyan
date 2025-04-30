import tkinter as tk
from tkinter import messagebox, scrolledtext
import datetime
import re
import os
import json
import requests
import traceback
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the module (with underscores instead of spaces in the name)
import Travel_Plan_and_booking_api as travel_api

class TravelUI:
    def __init__(self, root):
        self.root = root
        self.main_frame = tk.Frame(root, padx=20, pady=20)

        # Create frames
        self.input_frame = tk.LabelFrame(self.main_frame, text="Trip Details", padx=15, pady=15)
        self.input_frame.pack(fill=tk.X, pady=(0, 15))

        # Add text input field for natural language processing
        self.nlp_label = tk.Label(self.input_frame,
                                  text="Describe your trip:",
                                  anchor="w")
        self.nlp_label.pack(anchor="w", pady=(0, 5))

        self.nlp_text = tk.Text(self.input_frame, height=6, width=60)
        self.nlp_text.pack(fill=tk.X, pady=(0, 10))
        self.nlp_text.insert(tk.END,
                             "Example: I want to travel from Delhi to Mumbai on May 1, 2025 and return on May 5, 2025 with 1 adult and a budget of $10,000")

        # Add click event to clear example text
        self.nlp_text.bind("<FocusIn>", self.clear_example_text)

        self.extract_button = tk.Button(self.input_frame, text="Plan My Trip",
                                        command=self.process_trip_details,
                                        bg="#4CAF50", fg="white", padx=10)
        self.extract_button.pack(pady=(0, 5))

        # Back button
        self.back_button = tk.Button(self.main_frame, text="Back", command=None)
        self.back_button.pack(side=tk.BOTTOM, pady=(10, 0))

        # Results frame
        self.result_frame = tk.LabelFrame(self.main_frame, text="Travel Suggestions", padx=15, pady=15)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.results_text = scrolledtext.ScrolledText(self.result_frame, wrap=tk.WORD,
                                                      width=80, height=15,
                                                      font=("Arial", 11))
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.config(state=tk.DISABLED)

        # Package selection frame (initially hidden)
        self.package_frame = tk.Frame(self.main_frame)

        tk.Label(self.package_frame, text="Select package number:").pack(side=tk.LEFT, padx=(0, 10))
        self.package_entry = tk.Entry(self.package_frame, width=5)
        self.package_entry.pack(side=tk.LEFT)

        self.book_button = tk.Button(self.package_frame, text="Book Package",
                                     command=self.book_package,
                                     bg="#4CAF50", fg="white", padx=10)
        self.book_button.pack(side=tk.LEFT, padx=(10, 0))

    def clear_example_text(self, event):
        """Clear the example text when the user clicks in the text field"""
        if self.nlp_text.get("1.0", tk.END).strip().startswith("Example:"):
            self.nlp_text.delete("1.0", tk.END)

    def show(self, return_callback):
        # Set up the back button callback
        self.back_button.config(command=return_callback)

        # Show main frame
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Reset results
        self.update_results("Describe your trip above and click 'Plan My Trip'")

        # Set focus to text field
        self.nlp_text.focus_set()

        # Hide package selection initially
        self.package_frame.pack_forget()

    def hide(self):
        # Hide the main frame
        self.main_frame.pack_forget()

    def process_trip_details(self):
        """Process the trip description and search for travel options"""
        try:
            text_input = self.nlp_text.get("1.0", tk.END).strip()
            if not text_input or text_input.startswith("Example:"):
                messagebox.showinfo("Input Required", "Please describe your trip in the text box.")
                return

            self.update_results("Processing your trip details...\nThis may take a moment.")
            self.root.update()

            # Extract travel details from text using the imported module
            travel_data = travel_api.extract_travel_details(text_input)

            if not travel_data:
                self.update_results(
                    "Sorry, I couldn't understand the trip details. Please try again with more specific information.")
                return

            # Print extracted details to terminal
            print("\nExtracted Travel Details:")
            print(f"Origin: {travel_data.get('origin', 'Unknown')}")
            print(f"Destination: {travel_data.get('destination', 'Unknown')}")
            print(f"Departure date: {travel_data.get('departure_date', 'Unknown')}")
            print(f"Return date: {travel_data.get('return_date', 'Unknown')}")
            print(f"Adults: {travel_data.get('adults', '1')}")
            print(f"Budget: ${travel_data.get('budget', '1000')}")

            # Get the extracted values
            origin = travel_data.get('origin', '')
            destination = travel_data.get('destination', '')
            departure_date = travel_data.get('departure_date', '')
            return_date = travel_data.get('return_date', '')

            try:
                adults = int(str(travel_data.get('adults', '1')))
            except ValueError:
                adults = 1

            try:
                budget_str = str(travel_data.get('budget', '1000'))
                # Remove $ and , from the budget string
                budget_str = budget_str.replace('$', '').replace(',', '')
                budget = float(budget_str)
            except ValueError:
                budget = 1000

            # Validate the extracted data
            if not origin or not destination or not departure_date or not return_date:
                self.update_results("Some travel details are missing. Please provide more specific information.")
                return

            # Update status
            self.update_results(
                f"Searching for travel options from {origin} to {destination}...\nThis may take a few moments.")
            self.root.update()

            # Search for flights
            flight_offers, flight_message = travel_api.search_flights(origin, destination, departure_date, return_date, adults)

            if not flight_offers:
                self.update_results(f"No flights found: {flight_message}")
                return

            # Search for hotels
            hotel_offers, hotel_message = travel_api.fetch_room_details(destination, departure_date, return_date, adults)

            if not hotel_offers:
                self.update_results(f"No hotels found: {hotel_message}")
                return

            # Create travel packages
            packages = travel_api.create_travel_packages(flight_offers, hotel_offers, budget)

            if not packages:
                self.update_results("Couldn't create any suitable travel packages.")
                return

            # Display package options
            result_text = f"Found {len(packages)} travel package options for you!\n\n"
            result_text += f"Trip from {origin} to {destination}\n"
            result_text += f"Departure: {departure_date} - Return: {return_date}\n\n"

            for package in packages:
                result_text += travel_api.format_travel_package(package)

            self.update_results(result_text)

            # Store packages for later booking
            self.packages = packages
            self.trip_details = {
                'origin': origin,
                'destination': destination,
                'departure_date': departure_date,
                'return_date': return_date,
                'adults': adults
            }

            # Show package selection frame
            self.package_frame.pack(before=self.back_button, pady=(0, 10))

        except Exception as e:
            self.update_results(f"Error processing trip details: {str(e)}")
            traceback.print_exc()

    def book_package(self):
        try:
            if not hasattr(self, 'packages') or not self.packages:
                messagebox.showerror("Error", "No packages available to book")
                return

            # Get selected package ID
            try:
                selected_id = int(self.package_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid package number")
                return

            # Find the selected package
            selected_package = next((p for p in self.packages if p['package_id'] == selected_id), None)

            if not selected_package:
                messagebox.showerror("Error", f"Package {selected_id} not found")
                return

            # Confirm booking
            confirm = messagebox.askyesno("Confirm Booking",
                                          f"Book Package {selected_id} for ${selected_package['total_price']:.2f}?")

            if not confirm:
                return

            # Use default traveler info instead of collecting it
            default_travelers = [{
                'id': 1,
                'dateOfBirth': '1980-01-01',
                'name': {'firstName': 'Test', 'lastName': 'Traveler'},
                'gender': 'MALE',
                'contact': {'emailAddress': 'test@example.com',
                            'phones': [{'deviceType': 'MOBILE', 'number': '1234567890'}]}
            }]

            # Book flight
            self.update_results("Processing booking...\nPlease wait...")
            self.root.update()

            flight_booked, flight_message = travel_api.book_flight(selected_package['flight'], default_travelers)

            if not flight_booked:
                messagebox.showerror("Booking Error", f"Flight booking failed: {flight_message}")
                return

            # Book hotel
            hotel_booked, hotel_message = travel_api.book_hotel(selected_package['hotel'], default_travelers)

            if not hotel_booked:
                messagebox.showerror("Booking Error", f"Hotel booking failed: {hotel_message}")
                return

            # Show success message
            result = f"🎉 Your trip is booked!\n\n"
            result += f"From {self.trip_details['origin']} to {self.trip_details['destination']}\n"
            result += f"Departure: {self.trip_details['departure_date']} - Return: {self.trip_details['return_date']}\n"
            result += f"Total cost: ${selected_package['total_price']:.2f}\n\n"
            result += f"{flight_message}\n{hotel_message}"

            self.update_results(result)
            messagebox.showinfo("Success", "Your trip has been successfully booked!")

            # Hide package selection once booked
            self.package_frame.pack_forget()

        except Exception as e:
            messagebox.showerror("Booking Error", str(e))
            traceback.print_exc()

    def update_results(self, result_text):
        # Update the results text widget
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, result_text)
        self.results_text.config(state=tk.DISABLED)