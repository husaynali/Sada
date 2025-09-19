import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from datetime import datetime
class AJNETScraper:
    def __init__(self):
        self.base_url = "https://www.ajnet.me/"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.categories = {
            'politics': "politics/",
            'business': "ebusiness/",
            'culture': "culture/",
            'sport': "sport/",
            'tech': "tech/",
            'opinion': "opinion/",
            'turath': "turath/",
            'arts': "arts/",
            'science': "science/",
            'midan': "midan/",
            'lifestyle': "lifestyle/",
            'family': "family/",
        }

    def get_article_text(self, article_url):
        """Fetch full article text from an article URL"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find("div", class_="wysiwyg") or soup
            article_text = ' '.join([p.get_text(strip=True) for p in content.find_all('p')])
            return article_text
        except Exception as e:
            print(f"❌ Error fetching {article_url}: {e}")
            return ""

    def scrape_articles_from_category(self, category_url, category):
        """Scrape all articles from a given category URL"""
        try:
            response = requests.get(category_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('a', class_='u-clickable-card__link')

            data = []
            for article in articles:
                title_tag = article.find('span')
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                article_url = urljoin(category_url, article['href'])
                full_text = self.get_article_text(article_url)
                if full_text:
                    data.append({
                        'Category': category,
                        'Title': title,
                        'Link': article_url,
                        'Text': full_text
                    })
            return data
        except Exception as e:
            print(f"❌ Error scraping {category_url}: {e}")
            return []

    def scrape_all_categories(self):
        """Scrape all categories and return a DataFrame"""
        all_data = []
        for category, path in self.categories.items():
            category_url = urljoin(self.base_url, path)
            print(f"🔎 Scraping category: {category}")
            data = self.scrape_articles_from_category(category_url, category)
            all_data.extend(data)

        df = pd.DataFrame(all_data)
        return df

    def save_csv(self, df, folder=".", prefix="Ajnet"):
        """Save the DataFrame to a CSV with date-stamped filename"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{folder}/{prefix}-{today}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ Saved {len(df)} articles to {filename}")
        return filename
