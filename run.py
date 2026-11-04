import uvicorn
import sys
import os

# Set stdout/stderr encoding to UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("================================================================")
    print("Starting Shahid Smriti Residential Secondary School Server")
    print("Shahid Smriti Awasiya Madhyamik Vidyalaya, Itahari-19, Sunsari")
    print("URL: http://localhost:3000/")
    print("================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=False, access_log=True)
