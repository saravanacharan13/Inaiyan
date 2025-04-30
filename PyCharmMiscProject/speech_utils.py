# speech_utils.py
import azure.cognitiveservices.speech as speechsdk
import threading
import os
from dotenv import load_dotenv


class SpeechUtils:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Try to use existing OpenAI API credentials if they exist
        # Check for dedicated speech keys first
        self.speech_key = os.environ.get("AZURE_SPEECH_KEY")

        # If no dedicated speech key, try to use the OpenAI API key
        if not self.speech_key:
            self.speech_key = os.environ.get("AZURE_OPENAI_API_KEY")

        self.speech_region = os.environ.get("AZURE_SPEECH_REGION")

        # If no speech region, try to use the OpenAI API region
        if not self.speech_region:
            self.speech_region = os.environ.get("AZURE_OPENAI_API_REGION", "eastus")

        # Check if we have any valid key
        if not self.speech_key:
            print("WARNING: No valid Azure Speech or OpenAI API key found in .env file. Speech features will not work.")
            self.service_available = False
        else:
            self.service_available = True
            print(f"Azure Speech Service configured with region: {self.speech_region}")

        # Initialize speech config if service is available
        if self.service_available:
            try:
                self.speech_config = speechsdk.SpeechConfig(
                    subscription=self.speech_key,
                    region=self.speech_region
                )
            except Exception as e:
                print(f"Error initializing speech config: {e}")
                self.service_available = False

        # For tracking the listening state
        self.is_listening = False
        self.listen_thread = None

    def recognize_speech(self, language="en-IN", callback=None):
        """
        Recognize speech using Azure Speech SDK
        language: "en-IN" for English (India), "ta-IN" for Tamil
        """
        if not self.service_available:
            print("Speech recognition unavailable: No valid API key")
            return ""

        try:
            # Set the recognition language
            self.speech_config.speech_recognition_language = language

            # Create audio config using default microphone
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            print(f"Listening for {language}...")

            # Start speech recognition
            result = speech_recognizer.recognize_once()

            # Process the result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text
                print(f"Recognized: {recognized_text}")
                if callback:
                    callback(recognized_text)
                return recognized_text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("No speech could be recognized")
                return ""
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"Speech recognition canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation.error_details}")
                return ""
        except Exception as e:
            print(f"Error in speech recognition: {e}")
            return ""

    def start_listening(self, language="en-IN", callback=None):
        """Start listening in a separate thread"""
        if not self.service_available:
            print("Speech recognition unavailable: No valid API key")
            if callback:
                callback("")
            return False

        if self.is_listening:
            return False

        self.is_listening = True
        self.listen_thread = threading.Thread(
            target=self._listen_thread_func,
            args=(language, callback)
        )
        self.listen_thread.daemon = True
        self.listen_thread.start()
        return True

    def _listen_thread_func(self, language, callback):
        try:
            text = self.recognize_speech(language, None)
            # We handle the callback here to ensure UI updates happen properly
            if text and callback:
                callback(text)
        finally:
            self.is_listening = False

    def speak_text(self, text, language="en-IN"):
        """
        Convert text to speech using Azure Speech SDK
        language: "en-IN" for English (India), "ta-IN" for Tamil
        """
        if not self.service_available:
            print("Text-to-speech unavailable: No valid API key")
            return False

        try:
            # Configure voice based on language
            if language == "ta-IN":
                self.speech_config.speech_synthesis_voice_name = "ta-IN-PallaviNeural"
            else:
                self.speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"

            # Create speech synthesizer
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)

            # Synthesize speech
            result = speech_synthesizer.speak_text_async(text).get()

            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("Speech synthesis completed")
                return True
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"Speech synthesis canceled: {cancellation.reason}")
                return False
        except Exception as e:
            print(f"Error in speech synthesis: {e}")
            return False

    def speak_text_non_blocking(self, text, language="en-IN"):
        """Speak text in a non-blocking way"""
        if not self.service_available:
            return None

        thread = threading.Thread(target=self.speak_text, args=(text, language))
        thread.daemon = True
        thread.start()
        return thread