from engine import AssistantEngine

def main():
    engine = AssistantEngine()
    print("Assistant v1 online. Type 'exit' to quit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        
        response = engine.handle(user_input)
        print("Assistant:", response)

if __name__ == "__main__":
    main()