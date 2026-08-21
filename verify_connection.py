import os
from dotenv import load_dotenv

# Load environmental configurations
load_dotenv()

from backend.providers.bedrock import get_model
from strands import Agent

def main():
    print("==================================================")
    print("ContractorOS Assurance Agent - Connectivity Proof")
    print("==================================================")
    
    print("\n[1/3] Loading Model Provider...")
    model = get_model()
    print(f"-> Model provider loaded: {model.__class__.__name__} (ID: {getattr(model, 'model_id', 'Unknown')})")

    print("\n[2/3] Initializing Strands Agent...")
    agent = Agent(model=model)
    print("-> Strands Agent initialized successfully.")

    print("\n[3/3] Running test invocation...")
    prompt = "Hello! This is a verification request for Milestone 1."
    print(f"-> Sending prompt: '{prompt}'")
    
    try:
        response = agent(prompt)
        print("\n=== Agent Response ===")
        print(response)
        print("======================\n")
        print("[SUCCESS] Strands Agent connection verified and running successfully!")
    except Exception as e:
        print(f"\n[ERROR] Agent execution failed: {e}")
        raise e

if __name__ == "__main__":
    main()
