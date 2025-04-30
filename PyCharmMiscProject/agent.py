# agent.py
import openai
import re
from translator import translate_text
from config import (
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION
)


class NegotiationAgent:
    def __init__(self):
        self.context = ""
        self.max_price = 0
        self.target_price = 0
        self.local_language = "ta"  # Default is Tamil
        self.conversation_history = []
        self.repeated_final_price_count = 0
        self.last_price = None
        self.deal_status = "negotiating"  # Can be "negotiating", "completed", "rejected"
        self.seller_type = "seller"  # Dynamic seller type based on context
        self.client = openai.AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )

    def setup_negotiation(self, context, max_price, local_language="ta"):
        """Set up the negotiation parameters"""
        self.context = context
        self.max_price = float(max_price)
        self.target_price = self.max_price * 0.7  # Target 30% below max price
        self.local_language = local_language
        self.conversation_history = []
        self.repeated_final_price_count = 0
        self.last_price = None
        self.deal_status = "negotiating"

        # Determine seller type based on context
        self._determine_seller_type()

        setup_msg = f"Negotiation setup complete. You can start the conversation now."
        return setup_msg

    def setup_negotiation_from_full_context(self, full_context):
        """Extract context and max price from a single input and set up negotiation"""
        # Try to extract maximum price from the text
        max_price_pattern = r'max(?:imum)?\s*(?:price|amount)?\s*(?:is|of|:)?\s*(?:rs\.?|₹)?\s*(\d+)|(?:rs\.?|₹)?\s*(\d+)\s*(?:max(?:imum)?|at most)'

        # Also look for standalone price mentions with "willing to pay" context
        general_price = r'willing to pay\s*(?:rs\.?|₹)?\s*(\d+)|(?:rs\.?|₹)?\s*(\d+)\s*(?:max|maximum|at most|limit)'

        # Try different patterns
        price_match = re.search(max_price_pattern, full_context.lower())
        if not price_match:
            price_match = re.search(general_price, full_context.lower())

        # Try to find any number following currency symbols as last resort
        if not price_match:
            price_match = re.search(r'(?:rs\.?|₹)\s*(\d+)', full_context.lower())

        # Fallback to finding the last number in the string
        if not price_match:
            numbers = re.findall(r'\b(\d+)\b', full_context)
            max_price = 500  # Default fallback price
            if numbers:
                max_price = numbers[-1]  # Use the last number mentioned
        else:
            # Use the first non-None group from the regex match
            groups = price_match.groups()
            max_price = next((g for g in groups if g is not None), "500")

        # Remove price-related information from context
        context = re.sub(
            r'(?:max(?:imum)?\s*(?:price|amount)?\s*(?:is|of|:)?\s*(?:rs\.?|₹)?\s*\d+)|(?:rs\.?|₹)?\s*\d+\s*(?:max(?:imum)?|at most)',
            '', full_context, flags=re.IGNORECASE)
        context = re.sub(r'willing to pay\s*(?:rs\.?|₹)?\s*\d+|(?:rs\.?|₹)?\s*\d+\s*(?:max|maximum|at most|limit)', '',
                         context, flags=re.IGNORECASE)
        context = context.strip()

        # Debug info
        print(f"DEBUG: Extracted max price: {max_price}")
        print(f"DEBUG: Extracted context: {context}")

        # Set up the negotiation
        return self.setup_negotiation(context, max_price)

    def _determine_seller_type(self):
        """Determine seller type based on the context"""
        context_lower = self.context.lower()

        # Check for specific names first
        name_match = re.search(r'([A-Z][a-z]+)', self.context)
        if name_match and len(name_match.group(1)) > 2:
            self.seller_type = name_match.group(1)
            return

        # Check for specific types of sellers
        if any(keyword in context_lower for keyword in ["fish", "seafood", "meen"]):
            self.seller_type = "fish seller"
        elif any(keyword in context_lower for keyword in ["auto", "taxi", "cab", "ride", "driver"]):
            self.seller_type = "auto driver"
        elif any(keyword in context_lower for keyword in ["food", "restaurant", "meal", "chef"]):
            self.seller_type = "restaurant owner"
        elif any(keyword in context_lower for keyword in ["hotel", "room", "accommodation", "stay"]):
            self.seller_type = "hotel manager"
        elif any(keyword in context_lower for keyword in ["vegetable", "fruit", "grocery", "market"]):
            self.seller_type = "vendor"
        elif any(keyword in context_lower for keyword in ["clothes", "dress", "fashion", "apparel", "saree"]):
            self.seller_type = "shopkeeper"
        elif any(keyword in context_lower for keyword in ["electronic", "gadget", "phone", "laptop"]):
            self.seller_type = "electronics dealer"
        elif any(keyword in context_lower for keyword in ["jewelry", "gold", "silver"]):
            self.seller_type = "jeweler"
        else:
            self.seller_type = "seller"  # Default

    def get_starting_offer(self):
        """Generate an initial offer based on the context"""
        system_prompt = f"""
You are an expert negotiation assistant helping someone bargain in a market.
Context: {self.context}
Maximum price willing to pay: {self.max_price}
You should craft an initial greeting and ASK about the price first - don't mention any amount yet.
When referring to the person you're negotiating with, use "{self.seller_type}" not "seller".
Keep your response conversational, friendly, and concise.
"""

        try:
            response = self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.7
            )
            english_response = response.choices[0].message.content.strip()
        except Exception:
            english_response = f"Hello! I'm interested in this {self.context}. How much does it cost?"

        return self.translate_response(english_response)

    def generate_response(self, user_input):
        """Generate a negotiation response based on the user input"""
        # Check if deal is already completed
        if self.deal_status != "negotiating":
            return self._generate_new_negotiation_prompt()

        # Use linguistic analysis to detect if input needs translation
        is_likely_english = self.is_proper_english(user_input)

        # Translate input to English if it's not proper English
        try:
            if not is_likely_english:
                english_input = translate_text(user_input, 'en')
            else:
                english_input = user_input
        except Exception:
            english_input = "The seller is asking for a higher price."

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": english_input})

        # Extract price mentions from the input first
        mentioned_price = self.extract_price(english_input)

        # Store the price if it's valid
        if mentioned_price is not None:
            self.last_price = mentioned_price
            print(f"DEBUG: Updated last price to: {self.last_price}")

        # Check for verbal agreement that could indicate a deal
        if self._detect_agreement(english_input):
            print("DEBUG: Verbal agreement detected")
            # If we have a last price and it's acceptable, accept the deal
            if self.last_price is not None and self.last_price <= self.max_price:
                self.deal_status = "completed"
                return self._create_deal_acceptance_response(self.last_price)

        # Debug print
        print(
            f"DEBUG: Mentioned price: {mentioned_price}, Last price: {self.last_price}, Count: {self.repeated_final_price_count}")

        # Check if price is at or below max price, if so we can accept right away
        if mentioned_price is not None and mentioned_price <= self.max_price:
            # If price is excellent (below target), accept immediately
            if mentioned_price <= self.target_price * 1.1:  # Within 10% of our target
                print(f"DEBUG: Price {mentioned_price} is excellent (below/near target {self.target_price}), accepting")
                self.deal_status = "completed"
                return self._create_deal_acceptance_response(mentioned_price)

            # If price was repeated and is acceptable, accept
            if self.last_price is not None and abs(mentioned_price - self.last_price) < 1:
                self.repeated_final_price_count += 1
                if self.repeated_final_price_count >= 1:  # Accept on first repetition if price is good
                    print(f"DEBUG: Price {mentioned_price} is acceptable and repeated, accepting")
                    self.deal_status = "completed"
                    return self._create_deal_acceptance_response(mentioned_price)

        # Continue with normal price negotiation
        # Check for repeated final price that needs user decision
        if mentioned_price is not None:
            if self.last_price is not None and abs(mentioned_price - self.last_price) < 1:
                self.repeated_final_price_count += 1
                print(f"DEBUG: Repeated price count increased to {self.repeated_final_price_count}")
                if self.repeated_final_price_count >= 2:
                    print(f"DEBUG: Price {mentioned_price} repeated multiple times, asking user for decision")
                    # Return the prompt for user decision
                    return self._ask_for_final_decision(mentioned_price)
            else:
                # Reset counter if price changes
                self.repeated_final_price_count = 0

        # Determine negotiation strategy based on mentioned price
        if mentioned_price is not None:
            next_offer = self.calculate_next_offer(mentioned_price)
        else:
            next_offer = self.max_price * 0.6  # Default next offer if no price mentioned

        # Prepare system message with negotiation strategy
        system_message = f"""
You are an expert negotiation assistant helping someone bargain in a market.
Context: {self.context}
Maximum price willing to pay: {self.max_price}
Target price: {self.target_price}
Current offered price from {self.seller_type}: {mentioned_price if mentioned_price is not None else 'unknown'}
Your next offer should be around: {next_offer}

Follow these negotiation principles:
1. Be polite and respectful while firmly negotiating
2. Never immediately accept the first price
3. Highlight value and quality, not just price
4. If the mentioned price is close to your maximum, try to close the deal with a slight increase
5. Keep responses conversational and concise
6. When referring to the person you're negotiating with, use "{self.seller_type}" not "seller"

Craft a natural negotiation response without explicitly stating these strategy details.
"""

        # Prepare conversation history for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]

        # Add last few conversation turns (limit to 6 for context)
        for turn in self.conversation_history[-6:]:
            messages.append(turn)

        try:
            response = self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.7
            )
            english_response = response.choices[0].message.content.strip()
        except Exception:
            # Fallback response
            if mentioned_price is not None and mentioned_price <= self.max_price:
                english_response = f"I understand. How about {next_offer}? That seems fair for this."
            else:
                english_response = "I appreciate that, but it's still a bit high for me. Could we find a middle ground?"

        # Add response to history
        self.conversation_history.append({"role": "assistant", "content": english_response})

        # Replace any remaining "seller" with the specific seller type
        english_response = english_response.replace("seller", self.seller_type).replace("Seller",
                                                                                        self.seller_type.capitalize())

        # Return translated response
        return self.translate_response(english_response)

    def _detect_agreement(self, text):
        """Detect if text indicates agreement to a price"""
        # Convert to lowercase for easier matching
        text_lower = text.lower()

        # Look for patterns that indicate agreement
        agreement_patterns = [
            r'\b(?:ok|okay|fine|deal|agreed|accept)\b',
            r'\bseri\b',  # Tamil agreement word
            r'\byes\b',
            r'\bagree\b',
            r'\btake it\b',
            r'\bwe have a deal\b',
            r'\blet\'s do it\b'
        ]

        # Check if any pattern is found
        for pattern in agreement_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _create_deal_acceptance_response(self, price):
        """Create a response accepting the deal at the given price"""
        english_response = f"Great! I accept your price of {price} rupees. Thank you for the deal."
        self.conversation_history.append({"role": "assistant", "content": english_response})

        # Mark deal as completed
        self.deal_status = "completed"

        # Return translated response
        response = self.translate_response(english_response)
        response["deal_completed"] = True
        response["final_price"] = price
        return response

    def _ask_for_final_decision(self, final_price):
        """Ask the user if they want to accept the final price"""
        english_message = f"The {self.seller_type} has repeated the price of {final_price} multiple times and seems firm on this amount. Would you like to accept this price? (Yes/No)"

        # Don't add to conversation history as this is a meta-question
        response = self.translate_response(english_message)
        response["request_final_decision"] = True
        response["final_price"] = final_price

        return response

    def handle_final_decision(self, accept):
        """Handle the user's final decision"""
        if accept:
            self.deal_status = "completed"
            english_response = f"Great! I'll accept your price of {self.last_price}. Thank you for the fair deal."
        else:
            self.deal_status = "rejected"
            english_response = f"I'm sorry, that price doesn't work for me. I'll have to look elsewhere. Thank you for your time."

        # Add response to history
        self.conversation_history.append({"role": "assistant", "content": english_response})

        response = self.translate_response(english_response)
        if accept:
            response["deal_completed"] = True
            response["final_price"] = self.last_price

        return response

    def _generate_new_negotiation_prompt(self):
        """Generate a prompt to start a new negotiation"""
        english_message = "Would you like to start a new negotiation? What are you trying to buy?"
        return self.translate_response(english_message)

    def reset_negotiation(self):
        """Reset the negotiation state"""
        self.conversation_history = []
        self.repeated_final_price_count = 0
        self.last_price = None
        self.deal_status = "negotiating"
        return "Ready for a new negotiation. What would you like to buy?"

    def is_proper_english(self, text):
        """
        Check if text is likely proper English rather than transliterated Tamil or Tamil script
        Returns True if the text is likely proper English
        """
        # If it contains non-ASCII characters, it's likely not English
        if not all(ord(c) < 128 for c in text):
            return False

        # Common English function words that rarely appear in transliterated Tamil
        english_markers = ["the", "and", "a", "an", "in", "on", "at", "with", "for",
                           "from", "to", "by", "is", "are", "was", "were", "be", "been",
                           "will", "would", "can", "could", "should", "may", "might",
                           "have", "has", "had", "they", "their", "them", "these", "those"]

        words = text.lower().split()

        # Check for key English indicators
        english_word_count = sum(1 for word in words if word in english_markers)

        # Check for common Tamil transliteration patterns
        tamil_patterns = [
            r'\b\d+\s*ku\b',  # "100 ku"
            r'\billa\b',  # "illa"
            r'\baagum\b',  # "aagum"
            r'\bpoi\b',  # "poi"
            r'\bintha\b',  # "intha"
            r'\brendu\b',  # "rendu"
            r'\bkonjam\b',  # "konjam"
            r'\bnu\b'  # "nu"
        ]

        has_tamil_patterns = any(re.search(pattern, text.lower()) for pattern in tamil_patterns)

        # If it has multiple English function words and no Tamil patterns, likely English
        if english_word_count >= 2 and not has_tamil_patterns:
            return True

        # If it has Tamil patterns or very few English function words, likely Tamil
        if has_tamil_patterns or english_word_count == 0:
            return False

        # General heuristic - if the text is short without Tamil patterns,
        # we consider it English (could be simple phrases like "ok" or "too high")
        return len(words) <= 3

    def extract_price(self, text):
        """Extract price mentions from text"""
        # Match patterns like "500 rupees" or "Rs 500" or just "500" with context
        price_patterns = [
            r'(\d+)\s*(?:rupees|rs\.?|₹)',
            r'(?:rupees|rs\.?|₹)\s*(\d+)',
            r'(\d+)(?=\s*(?:price|cost|pay|offer|amount))'
        ]

        for pattern in price_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                try:
                    # Handle both tuple and string matches
                    if isinstance(matches[0], tuple):
                        for value in matches[0]:
                            if value:  # Find first non-empty value
                                return float(value)
                    else:
                        return float(matches[0])
                except (ValueError, TypeError):
                    pass

        # Check for just numbers in specific contexts
        number_match = re.search(r'(\d+)', text)
        if number_match and any(
                word in text.lower() for word in ["price", "cost", "pay", "offer", "amount", "final", "last"]):
            try:
                return float(number_match.group(1))
            except ValueError:
                pass

        # Simple number detection as fallback
        numbers = re.findall(r'\b\d+\b', text)
        if len(numbers) == 1:  # If there's only one number in the text
            try:
                return float(numbers[0])
            except ValueError:
                pass

        return None

    def calculate_next_offer(self, current_price):
        """Calculate the next offer based on negotiation strategy"""
        if current_price <= self.target_price:
            # Great price - accept with small increase
            return min(current_price * 1.05, self.max_price)

        if current_price <= self.max_price:
            # Price is acceptable but try to get better
            # Offer halfway between current and target
            return (current_price + self.target_price) / 2

        if current_price <= self.max_price * 1.2:
            # Price is slightly above max - counter with slightly below max
            return self.max_price * 0.9

        # Price is way too high - counter with low offer
        return self.target_price

    def translate_response(self, english_text):
        """Translate response to both English and Tamil"""
        try:
            local_text = translate_text(english_text, self.local_language)
        except Exception:
            # Fallback translation if API fails
            local_text = "நான் புரிந்து கொள்கிறேன். தயவுசெய்து ஒரு நியாயமான விலையை வழங்குங்கள்."

        return {
            "english": english_text,
            "tamil": local_text
        }

    def get_seller_type(self):
        """Return the current seller type"""
        return self.seller_type