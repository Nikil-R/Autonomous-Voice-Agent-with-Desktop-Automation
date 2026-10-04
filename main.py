"""ApexCore Production Server Launcher."""

import sys
import uvicorn
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    print("\n" + "=" * 65)
    print("🚀 APEXCORE BACKEND SERVER INITIALIZING")
    print("Serving on http://127.0.0.1:8000")
    print("Interactive UI:       http://127.0.0.1:8000")
    print("Interactive Swagger:  http://127.0.0.1:8000/docs")
    print("=" * 65 + "\n")
    
    uvicorn.run(
        "api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
