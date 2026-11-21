
import os
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("AGORA_APP_ID")
CUSTOMER_ID = os.getenv("AGORA_CUSTOMER_ID")
CUSTOMER_SECRET = os.getenv("AGORA_CUSTOMER_SECRET")

BASE_URL = "https://preview.ai.agora.io/conversational-ai/v1/projects"

print("\n====================================")
print(" YATRAPILOT AI - AGORA AUTH TEST")
print("====================================")

# Check environment variables
if not all([APP_ID, CUSTOMER_ID, CUSTOMER_SECRET]):
    raise ValueError(
        "Missing Agora credentials. Check your .env file."
    )

# Actual API request
url = f"{BASE_URL}/{APP_ID}/agents"

try:
    response = requests.get(
        url,
        auth=(CUSTOMER_ID, CUSTOMER_SECRET),
        params={"limit": 5},
        timeout=20
    )

    print("\nHTTP Status:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        agents = data.get("data", {}).get("list", [])

        print("\nSUCCESS: Agora authentication verified!")
        print("API connection: Working")
        print("Existing agents:", len(agents))

        for agent in agents:
            print(
                "Agent:",
                agent.get("agent_name", "Unnamed"),
                "| ID:",
                agent.get("agent_id", "Unavailable")
            )

        print("\nAGORA TEST PASSED!")

    elif response.status_code == 401:
        print("\nAUTHENTICATION FAILED")
        print("Check your Customer ID and Customer Secret.")

    elif response.status_code == 403:
        print("\nACCESS FORBIDDEN")
        print("Check project permissions and API access.")

    else:
        print("\nAPI REQUEST FAILED")
        print("Response:", response.text[:1000])

except requests.exceptions.RequestException as error:
    print("\nNETWORK ERROR:", error)

print("\n====================================")
