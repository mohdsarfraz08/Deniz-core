import sys
from engine import AssistantEngine
from utils.logger import setup_logger
from core.monitoring.resource_monitor import ResourceMonitor

# Initialize Project Management Essentials
logger = setup_logger("Main")
monitor = ResourceMonitor()

def main():
    logger.info("Initializing Assistant Engine Phase 2.1...")
    
    try:
        engine = AssistantEngine()
        # Log initial system state for transparency (Ethical Step)
        monitor.get_system_stats()
        
        print("Assistant v2.1 (Core) online. Type 'exit' to quit.")

        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ["exit", "quit"]:
                    logger.info("Shutdown sequence initiated by user.")
                    break
                
                # Execution with error handling
                response = engine.handle(user_input)
                print(f"Assistant: {response}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Runtime Error during handling: {e}")
                print("Assistant: I encountered an internal error. Check logs.")

    except Exception as e:
        logger.critical(f"Failed to initialize Engine: {e}")
    finally:
        print("System offline.")

if __name__ == "__main__":
    main()