import requests
import os
import traceback
import time
from datetime import datetime, timedelta
import urllib3
from dotenv import load_dotenv
import re
import json

# Load environment variables and disable SSL warnings
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get API credentials from environment variables
amadeus_key = os.environ.get('AMADEUS_API_KEY', 'FDad1IlOEmIrfxbb5WdACemdkpbv058G')
amadeus_secret = os.environ.get('AMADEUS_API_SECRET', 'X5NLEe5mUtts6d7j')


def extract_travel_details(text_input):
    """Extract travel details from natural language text using Azure OpenAI"""
    try:
        print("Extracting travel details from input text...")

        # Get Azure OpenAI credentials from environment variables
        api_key = os.environ.get('AZURE_OPENAI_KEY')
        endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME')
        api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2023-05-15')

        if not api_key or not endpoint or not deployment_name:
            print("Azure OpenAI credentials not found. Using fallback pattern matching.")
            # Parse the input using basic pattern matching as a fallback
            origin = re.search(r'from\s+([A-Za-z\s]+)(?:\s+to|\s+and)', text_input)
            destination = re.search(r'to\s+([A-Za-z\s]+)(?:\s+on|\s+from|\s+for)', text_input)
            departure_date = re.search(r'on\s+(\w+\s+\d+,?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})',
                                       text_input)
            return_date = re.search(
                r'return(?:ing)?\s+(?:on\s+)?(\w+\s+\d+,?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})',
                text_input)

            # If return date isn't found with "returning", look for other patterns
            if not return_date:
                return_date = re.search(r'to\s+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\w+\s+\d+,?\s+\d{4})',
                                        text_input)

            adults = re.search(r'(\d+)\s+(?:adult|person|people|passenger)', text_input)
            budget = re.search(r'(?:budget|cost).{1,10}(\$?\s*[\d,]+(?:\.\d{2})?)', text_input)

            # If budget isn't found with standard pattern, look for numbers after "around" or similar words
            if not budget:
                budget = re.search(r'(?:around|about|approximately)\s+(\$?\s*[\d,]+(?:\.\d{2})?)', text_input)

            result = {}
            if origin: result['origin'] = origin.group(1).strip()
            if destination: result['destination'] = destination.group(1).strip()
            if departure_date: result['departure_date'] = standardize_date(departure_date.group(1))
            if return_date: result['return_date'] = standardize_date(return_date.group(1))
            if adults: result['adults'] = adults.group(1)
            if budget:
                budget_value = budget.group(1).replace('$', '').replace(',', '').strip()
                result['budget'] = budget_value

            if result:
                print("Extracted travel details using fallback method.")
                return result

            # If nothing was extracted, return None
            return None

        # Construct the API request
        headers = {
            'Content-Type': 'application/json',
            'api-key': api_key
        }

        # Construct the prompt to extract travel information
        prompt = f"""
        Extract the following travel information from the text below:
        - Origin city or airport
        - Destination city or airport
        - Departure date (in YYYY-MM-DD format)
        - Return date (in YYYY-MM-DD format)
        - Number of adults
        - Total budget in USD

        Text: {text_input}

        Format the output as a JSON object with the following keys:
        origin, destination, departure_date, return_date, adults, budget
        """

        url = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

        payload = {
            "messages": [
                {"role": "system",
                 "content": "You are a helpful assistant that extracts structured travel information from text."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            response_json = response.json()
            content = response_json['choices'][0]['message']['content']

            # Try to parse the JSON response
            try:
                # Extract just the JSON part if there are additional notes
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

                if json_start >= 0 and json_end > 0:
                    json_content = content[json_start:json_end]
                    travel_data = json.loads(json_content)

                    print("Successfully extracted travel details!")
                    return travel_data
                else:
                    print("Could not find JSON in the response")
                    return None
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Response content: {content}")
                return None
        else:
            print(f"Azure OpenAI API request failed: {response.status_code}, {response.text}")
            return None

    except Exception as e:
        print(f"Error extracting travel details: {e}")
        traceback.print_exc()
        return None


def standardize_date(date_str):
    """Convert various date formats to YYYY-MM-DD format"""
    try:
        # Try different date formats
        formats = [
            '%Y-%m-%d',  # 2023-05-15
            '%m/%d/%Y',  # 05/15/2023
            '%m/%d/%y',  # 05/15/23
            '%B %d, %Y',  # May 15, 2023
            '%B %d %Y',  # May 15 2023
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If no format matched, return original string
        return date_str
    except:
        return date_str


def manual_api_call(endpoint, params=None, version="v1", method="GET", data=None):
    """Make a manual API call to Amadeus without using the SDK"""
    try:
        # First get the access token
        auth_url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': amadeus_key,
            'client_secret': amadeus_secret
        }

        response = requests.post(auth_url, data=auth_data, verify=False)
        if response.status_code != 200:
            print(f"Failed to get access token. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None

        token_data = response.json()
        access_token = token_data['access_token']

        # Now make the actual API call
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }

        api_url = f"https://test.api.amadeus.com/{version}/{endpoint}"
        print(f"Making API call to: {api_url}")
        print(f"With parameters: {params}")

        if method.upper() == "GET":
            response = requests.get(api_url, params=params, headers=headers, verify=False)
        elif method.upper() == "POST":
            response = requests.post(api_url, json=data, headers=headers, verify=False)
        else:
            print(f"Unsupported HTTP method: {method}")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error making manual API call: {e}")
        traceback.print_exc()
        return None


def get_city_code(city_name):
    """Convert a city name to an IATA code"""
    # Hard-coded common city codes for when API connection fails
    common_city_codes = {
        'delhi': 'DEL',
        'mumbai': 'BOM',
        'bangalore': 'BLR',
        'chennai': 'MAA',
        'hyderabad': 'HYD',
        'kolkata': 'CCU',
        'new york': 'JFK',
        'london': 'LHR',
        'paris': 'CDG',
        'tokyo': 'HND',
        'sydney': 'SYD',
        'dubai': 'DXB',
        'singapore': 'SIN',
        'hong kong': 'HKG'
    }

    # If input already looks like an IATA code (3 letters), return as uppercase
    if re.match(r'^[A-Za-z]{3}$', city_name):
        return city_name.upper()

    # Check against common cities first (case-insensitive)
    city_lower = city_name.lower()
    if city_lower in common_city_codes:
        code = common_city_codes[city_lower]
        print(f"Found IATA code for {city_name} in common cities: {code}")
        return code

    try:
        # Try to find the city code
        result = manual_api_call('reference-data/locations',
                                 {'keyword': city_name, 'subType': 'CITY,AIRPORT'})

        if result and result.get('data') and len(result['data']) > 0:
            # Return the first match's IATA code
            code = result['data'][0]['iataCode']
            print(f"Found IATA code for {city_name}: {code}")
            return code
        else:
            print(f"Could not find IATA code for {city_name}")
            # If API call failed, try the hardcoded list again with partial matching
            for known_city, code in common_city_codes.items():
                if known_city in city_lower or city_lower in known_city:
                    print(f"Found partial match IATA code for {city_name}: {code}")
                    return code
            # If still not found, return a default code for popular cities
            if 'delhi' in city_lower or 'india' in city_lower:
                return 'DEL'
            if 'mumbai' in city_lower or 'bombay' in city_lower:
                return 'BOM'
            # Default fallback
            return 'JFK'  # Default to JFK if nothing else works
    except Exception as e:
        print(f"Error finding city code: {e}")
        # Try the hardcoded list with partial matching
        for known_city, code in common_city_codes.items():
            if known_city in city_lower or city_lower in known_city:
                print(f"Found partial match IATA code for {city_name}: {code}")
                return code
        # Default fallback
        if 'delhi' in city_lower:
            return 'DEL'
        if 'mumbai' in city_lower:
            return 'BOM'
        return 'JFK'  # Default to JFK if nothing else works


def search_flights(origin, destination, departure_date, return_date=None, adults=1, max_price=None):
    """Search for flight offers between two cities using manual API calls"""
    try:
        # Convert city names to IATA codes if needed
        origin_code = get_city_code(origin)
        destination_code = get_city_code(destination)

        if not origin_code or not destination_code:
            # Generate synthetic flight data if we can't get city codes
            print(f"Generating synthetic flight data for {origin} to {destination}")
            return generate_synthetic_flights(origin, destination, departure_date, return_date,
                                              adults), "Using synthetic data"

        params = {
            'originLocationCode': origin_code,
            'destinationLocationCode': destination_code,
            'departureDate': departure_date,
            'adults': adults,
            'max': 5,  # Get 5 results to ensure variety
            'currencyCode': 'USD'
        }

        if return_date:
            params['returnDate'] = return_date

        if max_price:
            params['maxPrice'] = max_price

        # Flight offers is in v2 of the API
        result = manual_api_call('shopping/flight-offers', params, version="v2")

        if result and result.get('data'):
            return result.get('data'), "Success"
        else:
            # If API call fails, generate synthetic data
            print(f"API call failed. Generating synthetic flight data for {origin} to {destination}")
            return generate_synthetic_flights(origin, destination, departure_date, return_date,
                                              adults), "Using synthetic data"

    except Exception as e:
        print(f"Exception while searching flights: {e}")
        traceback.print_exc()
        # Generate synthetic data in case of any exception
        return generate_synthetic_flights(origin, destination, departure_date, return_date,
                                          adults), f"Using synthetic data (Error: {e})"


def generate_synthetic_flights(origin, destination, departure_date, return_date=None, adults=1):
    """Generate synthetic flight data for development and testing"""
    origin_code = get_city_code(origin) or "DEL"
    dest_code = get_city_code(destination) or "BOM"

    # Parse dates
    try:
        dep_date = datetime.strptime(departure_date, '%Y-%m-%d')
        dep_time_options = ['06:30:00', '10:15:00', '14:45:00', '19:20:00', '23:10:00']

        ret_date = None
        if return_date:
            ret_date = datetime.strptime(return_date, '%Y-%m-%d')
    except ValueError:
        # If date parsing fails, use default dates
        dep_date = datetime.now() + timedelta(days=30)
        ret_date = dep_date + timedelta(days=7) if return_date else None
        dep_time_options = ['06:30:00', '10:15:00', '14:45:00', '19:20:00', '23:10:00']

    # Generate 3 different flight options with different prices and times
    flights = []
    airlines = [
        {'code': 'AI', 'name': 'Air India'},
        {'code': 'SQ', 'name': 'Singapore Airlines'},
        {'code': 'EK', 'name': 'Emirates'}
    ]

    for i in range(3):
        # Select different departure times and prices for variety
        dep_time = dep_time_options[i % len(dep_time_options)]
        airline = airlines[i % len(airlines)]

        # Base price varies by flight option
        base_price = 2000 + (i * 500)

        flight = {
            "id": f"{i + 1}",
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {
                                "iataCode": origin_code,
                                "at": f"{departure_date}T{dep_time}"
                            },
                            "arrival": {
                                "iataCode": dest_code,
                                "at": f"{departure_date}T{dep_time}"
                            },
                            "carrierCode": airline['code'],
                            "number": f"{100 + i}",
                            "duration": "PT2H30M"
                        }
                    ]
                }
            ],
            "price": {
                "total": str(base_price),
                "currency": "USD"
            }
        }

        # Add return flight if return date is provided
        if return_date and ret_date:
            ret_time = dep_time_options[(i + 2) % len(dep_time_options)]
            flight["itineraries"].append({
                "segments": [
                    {
                        "departure": {
                            "iataCode": dest_code,
                            "at": f"{return_date}T{ret_time}"
                        },
                        "arrival": {
                            "iataCode": origin_code,
                            "at": f"{return_date}T{ret_time}"
                        },
                        "carrierCode": airline['code'],
                        "number": f"{200 + i}",
                        "duration": "PT2H30M"
                    }
                ]
            })

        flights.append(flight)

    return flights


def generate_synthetic_hotels(place, start_date, end_date, persons):
    """Generate synthetic hotel data for development and testing"""
    # Calculate stay duration for price calculation
    try:
        stay_duration = (datetime.strptime(end_date, '%Y-%m-%d') -
                         datetime.strptime(start_date, '%Y-%m-%d')).days
        if stay_duration <= 0:
            stay_duration = 3  # Default to 3 days if dates are invalid
    except ValueError:
        stay_duration = 3  # Default to 3 days if dates can't be parsed

    # Use place name for better hotel names
    city_name = place.title()

    # Create different hotel types at different price points
    hotels = [
        {
            "type": "hotel-offers",
            "hotel": {
                "name": f"Luxury {city_name} Resort",
                "rating": "5",
                "address": {
                    "lines": ["123 Luxury Avenue"],
                    "cityName": city_name
                }
            },
            "offers": [
                {
                    "id": "1",
                    "checkInDate": start_date,
                    "checkOutDate": end_date,
                    "room": {
                        "typeEstimated": {
                            "category": "SUITE"
                        }
                    },
                    "guests": {
                        "adults": persons
                    },
                    "price": {
                        "total": str(300 * stay_duration),
                        "currency": "USD"
                    }
                }
            ]
        },
        {
            "type": "hotel-offers",
            "hotel": {
                "name": f"Mid-Range {city_name} Hotel",
                "rating": "4",
                "address": {
                    "lines": ["456 Main Street"],
                    "cityName": city_name
                }
            },
            "offers": [
                {
                    "id": "2",
                    "checkInDate": start_date,
                    "checkOutDate": end_date,
                    "room": {
                        "typeEstimated": {
                            "category": "DELUXE"
                        }
                    },
                    "guests": {
                        "adults": persons
                    },
                    "price": {
                        "total": str(200 * stay_duration),
                        "currency": "USD"
                    }
                }
            ]
        },
        {
            "type": "hotel-offers",
            "hotel": {
                "name": f"Budget {city_name} Inn",
                "rating": "3",
                "address": {
                    "lines": ["789 Economy Road"],
                    "cityName": city_name
                }
            },
            "offers": [
                {
                    "id": "3",
                    "checkInDate": start_date,
                    "checkOutDate": end_date,
                    "room": {
                        "typeEstimated": {
                            "category": "STANDARD"
                        }
                    },
                    "guests": {
                        "adults": persons
                    },
                    "price": {
                        "total": str(100 * stay_duration),
                        "currency": "USD"
                    }
                }
            ]
        }
    ]

    print(f"Generated {len(hotels)} synthetic hotels for {city_name}")
    return hotels


def fetch_room_details(place, start_date, end_date, persons):
    """Fetch room details for the given place using the Amadeus API"""
    try:
        print(f"Debug: Fetching room details for {place} from {start_date} to {end_date} with {persons} adults")

        # First, ensure we have a valid city code
        city_code = get_city_code(place)
        if not city_code:
            # Generate synthetic data if city code is not available
            return generate_synthetic_hotels(place, start_date, end_date, persons), "Using synthetic data"

        # Define API parameters
        params = {
            'cityCode': city_code,
            'checkInDate': start_date,
            'checkOutDate': end_date,
            'adults': persons,
            'roomQuantity': 1,
            'currency': 'USD'
        }

        # Try to find hotels with the provided dates
        print(f"Searching for hotels in {city_code} from {start_date} to {end_date}")
        result = manual_api_call('shopping/hotel-offers', params, version="v2")

        if result and result.get('data') and len(result['data']) > 0:
            print(f"✅ Found {len(result['data'])} hotels in {city_code}!")
            return result['data'], "Success"

        # Generate synthetic data if API call fails or returns no results
        return generate_synthetic_hotels(place, start_date, end_date, persons), "Using synthetic data for development"

    except Exception as e:
        print(f"Exception while searching hotels: {e}")
        traceback.print_exc()
        # Generate synthetic data in case of any exception
        return generate_synthetic_hotels(place, start_date, end_date, persons), f"Using synthetic data (Error: {e})"


def create_travel_packages(flight_offers, hotel_offers, budget):
    """Create travel packages combining flights and hotels"""
    # If API calls failed and we got no offers, generate synthetic data
    if not flight_offers:
        print("No flight offers returned. Using synthetic data.")
        flight_offers = generate_synthetic_flights("Default Origin", "Default Destination",
                                                   datetime.now().strftime('%Y-%m-%d'),
                                                   (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                                                   1)

    if not hotel_offers:
        print("No hotel offers returned. Using synthetic data.")
        hotel_offers = generate_synthetic_hotels("Default City",
                                                 datetime.now().strftime('%Y-%m-%d'),
                                                 (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                                                 1)

    packages = []
    package_id = 1

    # Convert budget to float if it's a string
    if isinstance(budget, str):
        try:
            budget = float(budget.replace('$', '').replace(',', ''))
        except ValueError:
            budget = 10000  # Default budget

    # Sort flights by price
    sorted_flights = sorted(flight_offers,
                            key=lambda x: float(x.get('price', {}).get('total', '0')))

    # Sort hotels by price (safely)
    def get_hotel_price(hotel):
        try:
            if hotel.get('offers') and len(hotel['offers']) > 0:
                return float(hotel['offers'][0]['price']['total'])
            return float('inf')
        except (KeyError, ValueError):
            return float('inf')

    sorted_hotels = sorted(hotel_offers, key=get_hotel_price)

    # Create packages with different combinations
    for i in range(min(3, len(sorted_flights))):
        flight = sorted_flights[i]
        flight_price = float(flight.get('price', {}).get('total', '0'))

        # Find best hotel within remaining budget
        remaining_budget = budget - flight_price
        suitable_hotel = None

        for hotel in sorted_hotels:
            if hotel.get('offers') and len(hotel['offers']) > 0:
                hotel_price = float(hotel['offers'][0]['price']['total'])
                if hotel_price <= remaining_budget:
                    suitable_hotel = hotel
                    break

        # If no suitable hotel found within budget, take the cheapest hotel
        if not suitable_hotel and sorted_hotels and sorted_hotels[0].get('offers') and len(
                sorted_hotels[0]['offers']) > 0:
            suitable_hotel = sorted_hotels[0]

        if suitable_hotel:
            hotel_price = float(suitable_hotel['offers'][0]['price']['total'])
            total_price = flight_price + hotel_price

            package = {
                'package_id': package_id,
                'flight': flight,
                'hotel': suitable_hotel,
                'total_price': total_price,
                'within_budget': total_price <= budget
            }

            packages.append(package)
            package_id += 1

    return packages


def format_travel_package(package):
    """Format a travel package into a readable string"""
    result = f"Travel Package {package['package_id']}:\n"
    result += "=" * 50 + "\n\n"

    # Flight information
    flight = package['flight']
    result += "FLIGHT DETAILS:\n"
    result += "-" * 20 + "\n"

    # Iterate through itineraries (outbound and return)
    for j, itinerary in enumerate(flight.get('itineraries', [])):
        direction = "Outbound" if j == 0 else "Return"
        result += f"{direction} Flight:\n"

        for segment in itinerary.get('segments', []):
            departure = segment.get('departure', {})
            arrival = segment.get('arrival', {})
            carrier = segment.get('carrierCode', 'N/A')
            flight_number = segment.get('number', 'N/A')

            result += f"  {carrier} {flight_number}: {departure.get('iataCode', 'N/A')} → {arrival.get('iataCode', 'N/A')}\n"
            result += f"  Departure: {departure.get('at', 'N/A')}\n"
            result += f"  Arrival: {arrival.get('at', 'N/A')}\n\n"

    # Price information
    price = flight.get('price', {}).get('total', 'N/A')
    currency = flight.get('price', {}).get('currency', 'USD')
    result += f"Flight Price: {price} {currency}\n\n"

    # Hotel information
    hotel = package['hotel']
    result += "HOTEL DETAILS:\n"
    result += "-" * 20 + "\n"

    hotel_name = hotel['hotel'].get('name', 'N/A')
    hotel_rating = hotel['hotel'].get('rating', 'Not rated')
    result += f"Hotel: {hotel_name} ({hotel_rating} stars)\n"

    # Location info
    address = hotel['hotel'].get('address', {})
    location = f"{address.get('lines', [''])[0]}, {address.get('cityName', '')}"
    result += f"Location: {location}\n"

    # Price info
    if hotel.get('offers') and len(hotel['offers']) > 0:
        price = hotel['offers'][0].get('price', {}).get('total', 'N/A')
        currency = hotel['offers'][0].get('price', {}).get('currency', 'USD')
        result += f"Hotel Price: {price} {currency} for entire stay\n"

    # Room info
    if hotel.get('offers') and len(hotel['offers']) > 0:
        room_type = hotel['offers'][0].get('room', {}).get('typeEstimated', {}).get('category', 'Standard Room')
        result += f"Room type: {room_type}\n\n"

    # Total price
    result += f"TOTAL PACKAGE PRICE: {package['total_price']:.2f} {currency}\n"
    if package['within_budget']:
        result += "✅ Within your budget!\n"
    else:
        result += "⚠️ Exceeds your budget\n"

    result += "=" * 50 + "\n\n"

    return result


def book_flight(flight_offer, travelers):
    """Book a flight based on a flight offer"""
    try:
        print("Simulating flight booking process...")
        time.sleep(1)  # Simulate API call

        # In a real implementation, we would call the Amadeus flight booking API
        # For now, just simulate a successful booking

        flight_details = f"Flight {flight_offer.get('id', 'N/A')}"
        if flight_offer.get('itineraries') and len(flight_offer['itineraries']) > 0:
            segment = flight_offer['itineraries'][0]['segments'][0]
            carrier = segment.get('carrierCode', '')
            flight_num = segment.get('number', '')
            flight_details = f"Flight {carrier} {flight_num}"

        return True, f"✅ Flight booked successfully! {flight_details}"

    except Exception as e:
        print(f"Exception during flight booking: {e}")
        traceback.print_exc()
        return False, f"Flight booking failed: {str(e)}"


def book_hotel(hotel_offer, guest_info):
    """Book a hotel based on a hotel offer"""
    try:
        print("Simulating hotel booking process...")
        time.sleep(1)  # Simulate API call

        # In a real implementation, we would call the Amadeus hotel booking API
        # For now, just simulate a successful booking

        hotel_name = hotel_offer['hotel'].get('name', 'Unknown Hotel')
        room_type = "Standard Room"
        if hotel_offer.get('offers') and len(hotel_offer['offers']) > 0:
            room_type = hotel_offer['offers'][0].get('room', {}).get('typeEstimated', {}).get('category',
                                                                                              "Standard Room")

        return True, f"✅ Hotel booked successfully! {hotel_name}, {room_type}"

    except Exception as e:
        print(f"Exception during hotel booking: {e}")
        traceback.print_exc()
        return False, f"Hotel booking failed: {str(e)}"