from fastapi import FastAPI, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from datetime import datetime
import os
import pandas as pd

# Replace these with your actual scraper imports
from scrapers.ajnet_scraper import AJNETScraper
from scrapers.cnn_scraper import CNNScraper

# ----------------------
# Database setup
# ----------------------
DATABASE_URL = "sqlite:///./users.db"
database = Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True),
    Column("password_hash", String),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

# ----------------------
# App setup
# ----------------------
app = FastAPI(title="News Scraper API with Auth")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="super-secret-session-key")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CSV_FOLDER = "scraped_data"
os.makedirs(CSV_FOLDER, exist_ok=True)

# ----------------------
# Utility functions
# ----------------------
def get_csv_filename(prefix: str, date_str: str):
    return os.path.join(CSV_FOLDER, f"{prefix}-{date_str}.csv")

def scrape_if_missing(scraper_class, prefix: str, date_str: str):
    filename = get_csv_filename(prefix, date_str)
    if not os.path.exists(filename):
        scraper = scraper_class()
        df = scraper.scrape_all_categories()
        scraper.save_csv(df, folder=CSV_FOLDER, prefix=prefix)
    return filename

def get_current_user(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username

# ----------------------
# Startup & Shutdown
# ----------------------
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ----------------------
# Web routes: Signup/Login
# ----------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = request.session.get("user")
    html = "<h1>Welcome to News Scraper</h1>"
    if user:
        html += f"<p>Logged in as: {user}</p>"
        html += '<p><a href="/scrape">Go to Scrape</a></p>'
        html += '<p><a href="/logout">Logout</a></p>'
    else:
        html += '<p><a href="/signup">Sign Up</a></p>'
        html += '<p><a href="/login">Login</a></p>'
    return HTMLResponse(html)

@app.get("/signup", response_class=HTMLResponse)
async def signup_form():
    html_content = """
    <h2>Sign Up</h2>
    <form method="post">
        <input name="username" placeholder="Username" required/><br>
        <input name="password" type="password" placeholder="Password" required/><br>
        <button type="submit">Sign Up</button>
    </form>
    """
    return HTMLResponse(html_content)

@app.post("/signup")
async def signup_submit(username: str = Form(...), password: str = Form(...)):
    query = users.select().where(users.c.username == username)
    existing_user = await database.fetch_one(query)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = pwd_context.hash(password)
    query = users.insert().values(username=username, password_hash=hashed_password)
    await database.execute(query)
    return RedirectResponse("/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_form():
    html_content = """
    <h2>Login</h2>
    <form method="post">
        <input name="username" placeholder="Username" required/><br>
        <input name="password" type="password" placeholder="Password" required/><br>
        <button type="submit">Login</button>
    </form>
    """
    return HTMLResponse(html_content)

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    query = users.select().where(users.c.username == username)
    user = await database.fetch_one(query)
    if not user or not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    request.session["user"] = username
    return RedirectResponse("/", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/", status_code=302)

# ----------------------
# Scraping API
# ----------------------
@app.get("/scrape")
async def scrape(date: str = None, current_user: str = Depends(get_current_user)):
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    ajnet_csv = scrape_if_missing(AJNETScraper, "Ajnet", date)
    cnn_csv = scrape_if_missing(CNNScraper, "CNN-Arabic", date)

    df1 = pd.read_csv(ajnet_csv)
    df2 = pd.read_csv(cnn_csv)
    combined_df = pd.concat([df1, df2], ignore_index=True)

    combined_file = os.path.join(CSV_FOLDER, f"Combined-{date}.csv")
    combined_df.to_csv(combined_file, index=False, encoding="utf-8-sig")

    return FileResponse(combined_file, media_type="text/csv", filename=f"Combined-{date}.csv")

