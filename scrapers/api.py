from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
import os
import pandas as pd

from scrapers.ajnet_scraper import AJNETScraper
from scrapers.cnn_scraper import CNNScraper

app = FastAPI(title="News Scraper API")

CSV_FOLDER = "scraped_data"
os.makedirs(CSV_FOLDER, exist_ok=True)

def get_csv_filename(prefix: str, date_str: str):
    return os.path.join(CSV_FOLDER, f"{prefix}-{date_str}.csv")

def scrape_if_missing(scraper_class, prefix: str, date_str: str):
    filename = get_csv_filename(prefix, date_str)
    if not os.path.exists(filename):
        scraper = scraper_class()
        df = scraper.scrape_all_categories()
        scraper.save_csv(df, folder=CSV_FOLDER, prefix=prefix)
    return filename

@app.get("/scrape")
def scrape(date: str = Query(default=None, description="Date in YYYY-MM-DD, or leave empty for today")):
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

