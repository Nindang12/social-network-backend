import uvicorn
from API.api import app
from config import PORT

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT) 