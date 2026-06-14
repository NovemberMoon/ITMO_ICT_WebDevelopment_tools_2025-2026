import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re

def normalize_title(title: str) -> str:
    """
    Нормализует название для обеспечения строгой уникальности.
    Удаляет артикли, скобки, спецсимволы и приводит к нижнему регистру.
    """
    t = title.lower()
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'[^a-zа-я0-9\s]', '', t)
    return t.strip()

def fetch_real_urls():
    """Собирает 100 уникальных ссылок на книги с Project Gutenberg и Standard Ebooks."""
    print("Сбор 100 уникальных ссылок (50 Gutenberg + 50 Standard Ebooks)...")
    urls_file = Path(__file__).parent / "urls.txt"
    all_urls = []
    seen_titles = set()
    seen_urls = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    
    # 1. Project Gutenberg (50 уникальных ссылок)
    try:
        print("[1/2] Парсинг Project Gutenberg...")
        url = "https://www.gutenberg.org/browse/scores/top"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Проходим по всем спискам на странице (Топ за вчера, Топ за неделю)
        for ol in soup.find_all('ol'):
            for link in ol.find_all('a'):
                if len(all_urls) >= 50: break
                
                raw_title = link.text.strip()
                href = link.get('href', '')
                norm_title = normalize_title(raw_title)
                
                if href.startswith('/ebooks/') and norm_title not in seen_titles and len(norm_title) > 2:
                    seen_titles.add(norm_title)
                    seen_urls.add(href)
                    
                    display_title = re.sub(r'\s*\(\d+\)$', '', raw_title)
                    all_urls.append((f"[Gutenberg] {display_title}", f"https://www.gutenberg.org{href}"))
    except Exception as e:
        print(f"Ошибка Gutenberg: {e}")

    # 2. Standard Ebooks (50 уникальных ссылок)
    try:
        print("[2/2] Парсинг Standard Ebooks...")
        for page in range(1, 10):
            if len(all_urls) >= 100: break
            url = f"https://standardebooks.org/ebooks?page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for a_tag in soup.find_all('a'):
                if len(all_urls) >= 100: break
                
                href = a_tag.get('href', '')
                if href.startswith('/ebooks/') and len(href.split('/')) == 4:
                    raw_title = a_tag.text.strip()
                    if not raw_title: 
                        continue
                        
                    norm_title = normalize_title(raw_title)
                    
                    if href not in seen_urls and norm_title not in seen_titles and len(norm_title) > 2:
                        seen_titles.add(norm_title)
                        seen_urls.add(href)
                        all_urls.append((f"[Standard Ebooks] {raw_title}", f"https://standardebooks.org{href}"))
    except Exception as e:
        print(f"Ошибка Standard Ebooks: {e}")

    with open(urls_file, "w", encoding="utf-8") as f:
        for title, link in all_urls:
            f.write(f"# Книга: {title}\n")
            f.write(f"{link}\n\n")
            
    print(f"Успешно собрано {len(all_urls)} строго уникальных ссылок! Запускайте task2_runner.py")

if __name__ == "__main__":
    fetch_real_urls()