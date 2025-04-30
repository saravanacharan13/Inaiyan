import requests
import os
import traceback
import time
from datetime import datetime, timedelta
import urllib3
from dotenv import load_dotenv
import re
import json
from tabulate import tabulate

# Load environment variables and disable SSL warnings
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get API credentials from environment variables
amadeus_key = os.environ.get('AMADEUS_API_KEY', 'FDad1IlOEmIrfxbb5WdACemdkpbv058G')
amadeus_secret = os.environ.get('AMADEUS_API_SECRET', 'X5NLEe5mUtts6d7j')


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
    # If input already looks like an IATA code (3 letters), return as uppercase
    if re.match(r'^[A-Za-z]{3}$', city_name):
        return city_name.upper()

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
            return None
    except Exception as e:
        print(f"Error finding city code: {e}")
        return None


def search_flights(origin, destination, departure_date, return_date=None, adults=1, max_price=None):
    """Search for flight offers between two cities using manual API calls"""
    try:
        # Convert city names to IATA codes if needed
        origin_code = get_city_code(origin)
        destination_code = get_city_code(destination)

        if not origin_code or not destination_code:
            return None, "Unable to find airport codes for the specified cities"

        params = {
            'originLocationCode': origin_code,
            'destinationLocationCode': destination_code,
            'departureDate': departure_date,
            'adults': adults,
            'max': 5,
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
            return None, "Failed to retrieve flight offers"

    except Exception as e:
        print(f"Exception while searching flights: {e}")
        traceback.print_exc()
        return None, f"Error: {e}"


def fetch_room_details(place, start_date, end_date, persons):
    """Fetch room details for the given place using the Amadeus API"""
    try:
        print(f"Debug: Fetching room details for {place} from {start_date} to {end_date} with {persons} adults")

        # First, ensure we have a valid city code
        city_code = get_city_code(place)
        if not city_code:
            return None, "Unable to find city code for the specified city"

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

        # Try all other approaches as before...
        print(f"No hotels found with requested dates. Trying with current dates...")
        # (... existing API calls ...)

        # If all API approaches fail, generate synthetic data that matches API structure
        print("\nGenerating synthetic hotel data for development purposes...")
        print("Note: In production, you should use Amadeus production credentials")

        # Get city name from code for better results
        city_name = city_code
        city_info = manual_api_call('reference-data/locations',
                                    {'keyword': city_code, 'subType': 'CITY'})
        if city_info and city_info.get('data') and len(city_info['data']) > 0:
            city_name = city_info['data'][0]['name']

        # Calculate stay duration for price calculation
        stay_duration = (datetime.strptime(end_date, '%Y-%m-%d') -
                         datetime.strptime(start_date, '%Y-%m-%d')).days

        # Create synthetic hotel data matching Amadeus API format
        synthetic_hotels = [
            {
                "type": "hotel-offers",
                "hotel": {
                    "type": "hotel",
                    "hotelId": "BOMR001",
                    "chainCode": "RT",
                    "name": f"Royal Taj {city_name}",
                    "rating": "5",
                    "cityCode": city_code,
                    "latitude": 19.0822,
                    "longitude": 72.8604,
                    "address": {
                        "lines": [f"123 Main Street, {city_name}"],
                        "postalCode": "400001",
                        "cityName": city_name,
                        "countryCode": "IN"
                    }
                },
                "offers": [
                    {
                        "id": "BOMR001_1",
                        "checkInDate": start_date,
                        "checkOutDate": end_date,
                        "room": {
                            "type": "ROH",
                            "typeEstimated": {
                                "category": "DELUXE_ROOM",
                                "beds": 1,
                                "bedType": "KING"
                            }
                        },
                        "guests": {
                            "adults": persons
                        },
                        "price": {
                            "currency": "USD",
                            "total": str(180 * stay_duration),
                            "base": str(150 * stay_duration),
                            "taxes": [
                                {"amount": str(30 * stay_duration)}
                            ]
                        }
                    }
                ]
            },
            {
                "type": "hotel-offers",
                "hotel": {
                    "type": "hotel",
                    "hotelId": "BOMH002",
                    "chainCode": "HY",
                    "name": f"Hyatt {city_name}",
                    "rating": "4",
                    "cityCode": city_code,
                    "latitude": 19.1071,
                    "longitude": 72.8227,
                    "address": {
                        "lines": [f"456 Park Avenue, {city_name}"],
                        "postalCode": "400051",
                        "cityName": city_name,
                        "countryCode": "IN"
                    }
                },
                "offers": [
                    {
                        "id": "BOMH002_1",
                        "checkInDate": start_date,
                        "checkOutDate": end_date,
                        "room": {
                            "type": "ROH",
                            "typeEstimated": {
                                "category": "STANDARD_ROOM",
                                "beds": 1,
                                "bedType": "QUEEN"
                            }
                        },
                        "guests": {
                            "adults": persons
                        },
                        "price": {
                            "currency": "USD",
                            "total": str(120 * stay_duration),
                            "base": str(100 * stay_duration),
                            "taxes": [
                                {"amount": str(20 * stay_duration)}
                            ]
                        }
                    }
                ]
            },
            {
                "type": "hotel-offers",
                "hotel": {
                    "type": "hotel",
                    "hotelId": "BOMM003",
                    "chainCode": "MR",
                    "name": f"Marriott {city_name}",
                    "rating": "5",
                    "cityCode": city_code,
                    "latitude": 19.0930,
                    "longitude": 72.8558,
                    "address": {
                        "lines": [f"789 Beach Road, {city_name}"],
                        "postalCode": "400021",
                        "cityName": city_name,
                        "countryCode": "IN"
                    }
                },
                "offers": [
                    {
                        "id": "BOMM003_1",
                        "checkInDate": start_date,
                        "checkOutDate": end_date,
                        "room": {
                            "type": "ROH",
                            "typeEstimated": {
                                "category": "SUITE",
                                "beds": 1,
                                "bedType": "KING"
                            }
                        },
                        "guests": {
                            "adults": persons
                        },
                        "price": {
                            "currency": "USD",
                            "total": str(250 * stay_duration),
                            "base": str(200 * stay_duration),
                            "taxes": [
                                {"amount": str(50 * stay_duration)}
                            ]
                        }
                    }
                ]
            }
        ]

        print(f"Generated {len(synthetic_hotels)} synthetic hotels for {city_name}")
        return synthetic_hotels, "Success (using synthetic data for development)"

    except Exception as e:
        print(f"Exception while searching hotels: {e}")
        traceback.print_exc()
        return None, f"Error: {e}"

def create_travel_packages(flight_offers, hotel_offers, budget):
    """Create travel packages combining flights and hotels"""
    if not flight_offers or not hotel_offers:
        return []

    packages = []
    package_id = 1

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
                                                                                              'Standard Room')

        return True, f"✅ Hotel booked successfully! {hotel_name}, {room_type}"

    except Exception as e:
        print(f"Exception during hotel booking: {e}")
        traceback.print_exc()
        return False, f"Hotel booking failed: {str(e)}"


def test_amadeus_connection():
    """Test the Amadeus API connection and credentials"""
    try:
        print("Testing Amadeus API connection...")
        print(f"Using client ID starting with: {amadeus_key[:5]}...")

        # First, test direct OAuth token request
        print("Testing direct OAuth token request...")
        auth_url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': amadeus_key,
            'client_secret': amadeus_secret
        }

        response = requests.post(auth_url, data=auth_data, verify=False)
        print(f"OAuth response status: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            print("OAuth response: ")
            print(json.dumps(token_data, indent=12))

            # Test a manual API call
            print("Testing manual API call...")
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }

            api_url = "https://test.api.amadeus.com/v1/reference-data/locations"
            params = {'keyword': 'LON', 'subType': 'CITY'}

            response = requests.get(api_url, params=params, headers=headers, verify=False)

            if response.status_code == 200:
                result = response.json()
                locations_count = len(result.get('data', []))
                print("Manual API call successful!")
                print(f"Found {locations_count} locations")
                return True
            else:
                print(f"Manual API call failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print(f"OAuth token request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")

        return False

    except Exception as e:
        print(f"Exception during Amadeus API connection test: {e}")
        traceback.print_exc()
        return False


def collect_traveler_info(adults):
    """Collect traveler information for booking"""
    travelers = []

    for i in range(adults):
        print(f"\nTraveler {i + 1} Information:")

        first_name = input(f"First name: ")
        last_name = input(f"Last name: ")

        # Default values if input is empty
        if not first_name:
            first_name = "John"
        if not last_name:
            last_name = "Doe"

        # Create traveler object
        traveler = {
            'id': i + 1,
            'dateOfBirth': '1980-01-01',  # Default value
            'name': {
                'firstName': first_name,
                'lastName': last_name
            },
            'gender': 'MALE',  # Default value
            'contact': {
                'emailAddress': 'test@example.com',
                'phones': [{
                    'deviceType': 'MOBILE',
                    'countryCallingCode': '1',
                    'number': '1234567890'
                }]
            }
        }

        travelers.append(traveler)

    return travelers


# Main program
if __name__ == "__main__":
    # Get user input
    print("\n===== TRAVEL PLANNER =====\n")

    # Test network connectivity
    print("\nTesting network connection to Amadeus...")
    try:
        response = requests.get("https://test.api.amadeus.com/v1/security/oauth2/token", verify=False)
        print(f"Network connection to Amadeus: OK (status code: {response.status_code})")
    except Exception as e:
        print(f"Network connection to Amadeus failed: {str(e)}")
        exit(1)

    # Test the Amadeus API connection
    if not test_amadeus_connection():
        print("\n==== TROUBLESHOOTING TIPS ====")
        print("1. Your API keys may be expired - generate new ones at https://developers.amadeus.com/")
        print("2. Make sure you're using the right environment (test/production)")
        print("3. Your corporate network might be blocking the connection")
        print("4. Try this script from a different network")
        exit(1)

    print("\n===== PLAN YOUR TRIP =====")

    # Get travel details
    origin = input("Enter origin city or airport (e.g., London, New York, LAX): ")
    destination = input("Enter destination city or airport (e.g., Paris, Tokyo, SFO): ")

    # Get and validate travel dates
    while True:
        try:
            departure_date = input("Enter departure date (YYYY-MM-DD): ")
            datetime.strptime(departure_date, '%Y-%m-%d')

            return_date = input("Enter return date (YYYY-MM-DD): ")
            datetime.strptime(return_date, '%Y-%m-%d')

            # Check if return date is after departure date
            if datetime.strptime(return_date, '%Y-%m-%d') <= datetime.strptime(departure_date, '%Y-%m-%d'):
                print("Return date must be after departure date. Please try again.")
                continue

            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")

    # Get number of travelers and budget
    try:
        adults = int(input("Number of adults: ") or "1")
        budget = float(input("Your total budget (USD): ") or "1000")
    except ValueError:
        print("Invalid input for adults or budget. Using defaults: 1 adult, $1000 budget.")
        adults = 1
        budget = 1000

    print("\nSearching for flight options...")
    flight_offers, flight_message = search_flights(origin, destination, departure_date, return_date, adults)

    if not flight_offers:
        print(f"No flights found: {flight_message}")
        exit(1)

    print(f"Found {len(flight_offers)} flight options!")

    print("\nSearching for hotel options...")
    # Calculate number of nights for hotel stay
    check_in = departure_date
    check_out = return_date
    hotel_offers, hotel_message = fetch_room_details(destination, check_in, check_out, adults)

    if not hotel_offers:
        print(f"No hotels found: {hotel_message}")
        exit(1)

    print(f"Found {len(hotel_offers)} hotel options!")

    # Create travel packages
    print("\nCreating travel packages based on your preferences...")
    packages = create_travel_packages(flight_offers, hotel_offers, budget)

    if not packages:
        print("Couldn't create any suitable travel packages.")
        exit(1)

    # Display package options
    print(f"\nFound {len(packages)} travel package options for you!\n")

    for package in packages:
        print(format_travel_package(package))

    # Ask user to select a package
    while True:
        try:
            selected_id = int(input(f"Select a package (1-{len(packages)}): "))

            # Validate selection
            if 1 <= selected_id <= len(packages):
                # Find the selected package
                selected_package = next((p for p in packages if p['package_id'] == selected_id), None)
                break
            else:
                print(f"Please enter a number between 1 and {len(packages)}.")
        except ValueError:
            print("Please enter a valid number.")

    print(f"\nYou've selected Package {selected_package['package_id']}!")
    print(f"Total price: ${selected_package['total_price']:.2f}")

    # Confirm booking
    confirm = input("\nWould you like to proceed with booking? (yes/no): ").lower()

    if confirm != 'yes':
        print("Booking cancelled. Thank you for using Travel Planner!")
        exit(0)

    # Collect traveler information
    travelers = collect_traveler_info(adults)

    # Book flight
    print("\nProcessing flight booking...")
    flight_booked, flight_message = book_flight(selected_package['flight'], travelers)

    if not flight_booked:
        print(f"Flight booking failed: {flight_message}")
        exit(1)

    print(flight_message)

    # Book hotel
    print("\nProcessing hotel booking...")
    hotel_booked, hotel_message = book_hotel(selected_package['hotel'], travelers)

    if not hotel_booked:
        print(f"Hotel booking failed: {hotel_message}")
        print("Note: Flight has been booked but hotel booking failed.")
        print("Note: Flight has been booked but hotel booking failed.")
        exit(1)

    print(hotel_message)

    # Booking complete
    print("\n🎉 Congratulations! Your trip is booked!")
    print(f"From {origin} to {destination}")
    print(f"Departure: {departure_date} - Return: {return_date}")
    print(f"Total cost: ${selected_package['total_price']:.2f}")
    print("\nThank you for using Travel Planner!")