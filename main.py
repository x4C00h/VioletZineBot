import asyncio
from database import init_db
from bot import run_bot
import threading
import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import os
import database


# FASTAPI VARS
app = FastAPI()
templates = Jinja2Templates(directory="templates")
UPLOAD_FOLDER = 'works'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_web():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# LOCAL FUNCTIONS
@app.get("/", response_class=HTMLResponse())
async def index(request: Request):
    data = await database.get_page_data()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data
        }
    )

@app.get("/works/{work_id}.doc", response_class=FileResponse)
def download_file(work_id: int):
    filename = f"{work_id}.doc"
    path = os.path.join(BASE_DIR, UPLOAD_FOLDER, filename)
    
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/msword"
    )



async def main() -> None:
    await init_db()
    
    thread_web = threading.Thread(target=run_web, daemon=True)
    thread_web.start()

    await run_bot()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
