"""ApexCore Production Entry Point CLI."""

import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def check_environment():
    """Validates runtime prerequisites and keys."""
    if not GROQ_API_KEY:
        print("\n❌ Error: GROQ_API_KEY is not set in ApexCore/.env or environment.")
        print("Please configure your GROQ_API_KEY in ApexCore/.env before launching.\n")
        sys.exit(1)

async def main():
    check_environment()
    orchestrator = FullDuplexOrchestrator()
    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        print("\n🛑 ApexCore terminated gracefully by user.")
    except Exception as e:
        print(f"\n❌ Unexpected runtime error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
