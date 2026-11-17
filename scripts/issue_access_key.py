"""Issue a signed access key for a paying customer.

Usage (from the repository root, with ACCESS_KEY_SECRET set to the same value
the backend uses):

    python scripts/issue_access_key.py pro 30
    python scripts/issue_access_key.py plus 30
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from services import billing_service  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3 or not sys.argv[2].isdigit():
        print(__doc__)
        return 2
    plan, days = sys.argv[1].lower(), int(sys.argv[2])
    try:
        key = billing_service.issue_access_key(plan, days)
    except ValueError as err:
        print(f"Error: {err}")
        return 1
    print(f"{plan} access for {days} days:")
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
