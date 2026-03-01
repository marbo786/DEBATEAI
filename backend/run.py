"""Run the DebateAI API server."""
import sys
import os
import uvicorn

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=5000, reload=True)
