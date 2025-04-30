Travel & Negotiation Assistant:
A dual-purpose application providing market negotiation assistance and travel booking capabilities with a graphical user interface.


Features:
A. Market Negotiation Mode:
Helps users negotiate prices in markets in both English and Tamil
Voice input and output capabilities
Contextual responses based on seller type
Price tracking and negotiation strategy

B. Travel Booking Mode:
Search for flights and hotels
Package creation based on budget
Booking functionality


Installation:
1. Prerequisites
Python 3.8 or higher
Tkinter (usually comes with Python)

2.Setup
Install required libraries:

pip install -r requirements.txt
Or install individual packages:

pip install gtts pyttsx3 SpeechRecognition pyaudio
Usage

3.Run the application

python app.py

Working:


Choose "Market Negotiation" or "Travel Booking" from the main menu
Negotiation Mode

Negotiation Mode:

Enter details about who you're negotiating with and your budget
Use text or voice input to interact with the seller
Get real-time assistance in English and Tamil

Travel Mode:

Enter travel details including origin, destination, dates
View available travel packages
Book your preferred package


Project Structure:

app.py - Main application entry point
negotiation_ui.py - UI for the negotiation assistant
travel_ui.py - UI for the travel booking system
agent.py - Core negotiation agent logic
speech_utils.py - Speech recognition and synthesis utilities

Key Notes:
The negotiation assistant works best with clear speech input
Tamil language support requires internet connection for speech synthesis
Travel booking mode uses simulated APIs for demonstration purposes

Troubleshooting:
PyAudio installation issues:

Windows: pip install pipwin followed by pipwin install pyaudio
Linux: sudo apt-get install portaudio19-dev then pip install pyaudio
macOS: brew install portaudio then pip install pyaudio
Speech recognition not working:
Ensure your microphone is properly connected and has permissions
Check internet connection for speech recognition services