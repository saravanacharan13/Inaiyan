# main.py
from agent import NegotiationAgent


def main():
    agent = NegotiationAgent()

    print("Negotiation Agent")
    print("First, let's set up your negotiation")

    # Get negotiation context from user in a single input
    print("\nDescribe who you're negotiating with, what for, and your maximum price (e.g. 'I am with Auto driver, going from market to hotel, max 200 rupees'):")
    full_context = input("> ")

    # Set up the negotiation with combined input
    setup_result = agent.setup_negotiation_from_full_context(full_context)

    # Show the extracted context and max price
    print(f"\nUnderstood: Context: {agent.context}")
    print(f"Maximum price: ₹{agent.max_price}")

    # Get the seller type
    seller_type = agent.get_seller_type()

    # Generate starting message
    initial_response = agent.get_starting_offer()
    print("\nYour opening message:")
    print(f"English: {initial_response['english']}")
    print(f"Tamil: {initial_response['tamil']}")
    print("-" * 50)

    print("(Type 'exit' to end the conversation)")

    while True:
        # Use the dynamically determined seller type for input prompt
        user_input = input(f"\n{seller_type.capitalize()} says (in Tamil or English): ")

        if user_input.lower() == 'exit':
            break

        response = agent.generate_response(user_input)

        # Check if deal was automatically completed
        if "deal_completed" in response:
            print("\nYou respond:")
            print(f"English: {response['english']}")
            print(f"Tamil: {response['tamil']}")

            print("-" * 50)
            print("\nNegotiation result:")
            print(f"Deal status: {agent.deal_status.upper()} at price: ₹{response['final_price']}")
            print("-" * 50)

            # Ask if user wants to start a new negotiation
            start_new = handle_new_negotiation(agent)
            if not start_new:
                break

            # Update seller type for the new negotiation
            seller_type = agent.get_seller_type()
            continue

        # Check if we need user decision on final price
        if "request_final_decision" in response:
            print("\nDecision required:")
            print(f"English: {response['english']}")
            print(f"Tamil: {response['tamil']}")
            decision = input("\nDo you accept this price? (yes/no): ").lower()

            accept = decision in ['yes', 'y', 'accept', '1', 'true']
            response = agent.handle_final_decision(accept)

            # Show final message to the seller
            print("\nYou respond:")
            print(f"English: {response['english']}")
            print(f"Tamil: {response['tamil']}")

            if agent.deal_status != "negotiating":
                print("-" * 50)
                print("\nNegotiation result:")
                print(f"Deal status: {agent.deal_status.upper()} at price: ₹{agent.last_price}")
                print("-" * 50)

                # Ask if user wants to start a new negotiation
                start_new = handle_new_negotiation(agent)
                if not start_new:
                    break

                # Update seller type for the new negotiation
                seller_type = agent.get_seller_type()
                continue

        print("\nYou respond:")
        print(f"English: {response['english']}")
        print(f"Tamil: {response['tamil']}")
        print("-" * 50)


def handle_new_negotiation(agent):
    """Ask user if they want to start a new negotiation and handle setup"""
    new_negotiation = input("\nWould you like to start a new negotiation? (yes/no): ").lower()
    if new_negotiation in ['yes', 'y', '1', 'true']:
        # Get new negotiation context from user in a single input
        print("\nDescribe who you're negotiating with, what for, and your maximum price:")
        full_context = input("> ")

        # Set up the negotiation with combined input
        agent.setup_negotiation_from_full_context(full_context)

        # Show the extracted context and max price
        print(f"\nUnderstood: Context: {agent.context}")
        print(f"Maximum price: ₹{agent.max_price}")

        # Generate starting message
        initial_response = agent.get_starting_offer()
        print("\nYour opening message:")
        print(f"English: {initial_response['english']}")
        print(f"Tamil: {initial_response['tamil']}")
        print("-" * 50)
        return True
    else:
        return False


if __name__ == "__main__":
    main()