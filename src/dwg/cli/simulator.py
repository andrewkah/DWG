"""Interactive terminal USSD CLI simulator"""

import argparse
import sys
import uuid

from fastapi import requests


def run_simulator(
    base_url: str,
    service_code: str,
    phone_number: str,
    provider: str,
):
    session_id = f"sim-{uuid.uuid4().hex[:8]}"
    endpoint = f"{base_url.rstrip('/')}/api/v1/ussd/{provider}"

    print("\n" + "=" * 55)
    print("   DWG USSD TERMINAL SIMULATOR")
    print(f"   Target Short Code : {service_code}")
    print(f"   Subscriber Phone  : {phone_number}")
    print(f"   Provider Route    : {provider}")
    print(f"   Session ID        : {session_id}")
    print("=" * 55)
    print(f"Dialing {service_code}...\n")

    # Intial dail-in
    if provider == "africas_talking":
        payload = {
            "sessionId": session_id,
            "phoneNumber": phone_number,
            "serviceCode": service_code,
            "text": "",
        }
    else:
        payload = {
            "session_id": session_id,
            "phone_number": phone_number,
            "service_code": service_code,
            "text": "",
            "is_new": True,
        }

    accumulated_at_text = []

    while True:
        try:
            res = requests.post(endpoint, data=payload, timeout=5)
        except requests.exceptions.ConnectionError:
            print(
                f"[ERROR] Could not connect to DWG API at {base_url}. Is FastAPI running?"
            )
            sys.exit(1)

        raw_response = res.text
        if not (raw_response.startswith("CON ") or raw_response.startswith("END ")):
            print(f"[ERROR] Invalid telco response received:\n{raw_response}")
            sys.exit(1)

        action = raw_response[:3]
        prompt = raw_response[4:]

        if action == "CON":
            print(f"<--- [CON]\n{prompt}\n")
            user_input = input("> ").strip()

            if provider == "africas_talking":
                accumulated_at_text.append(user_input)
                payload["text"] = "*".join(accumulated_at_text)
            else:
                payload["text"] = user_input
                payload["is_new"] = False
        else:
            print(f"<--- [END]\n{prompt}\n")
            print("=" * 55)
            print("   SESSION TERMINATED BY NETWORK")
            print("=" * 55 + "\n")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DWG Interactive USSD Terminal Simulator"
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="Base URL of DWG API"
    )
    parser.add_argument("--code", default="*384*100#", help="Short code to dial")
    parser.add_argument(
        "--phone", default="+256770123456", help="Subscriber phone number"
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "africas_talking"],
        default="mock",
        help="Target provider adapter",
    )
    args = parser.parse_args()

    run_simulator(args.url, args.code, args.phone, args.provider)
