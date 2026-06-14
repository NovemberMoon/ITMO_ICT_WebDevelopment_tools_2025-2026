import uuid
import math
import re
from pathlib import Path
from bs4 import BeautifulSoup

def load_urls(filename: str = "urls.txt") -> list[str]:
    """Загружает URL-ы из текстового файла, игнорируя пустые строки и комментарии."""
    file_path = Path(__file__).parent / filename
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"):
                    urls.append(url)
    except FileNotFoundError:
        print(f"[Ошибка] Файл {filename} не найден!")
    return urls

def divide_into_chunks(lst: list, num_chunks: int) -> list[list]:
    """Разделяет список на равные части."""
    if not lst: return []
    chunk_size = math.ceil(len(lst) / num_chunks)
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def extract_book_info(html: str, url: str) -> dict:
    """Извлекает информацию о книге из HTML-кода страницы."""
    soup = BeautifulSoup(html, 'html.parser')
    
    title = "Неизвестное название"
    author = "Неизвестный автор"
    year = 1900
    isbn = "N/A"
    language = "en"
    description = "Описание недоступно."
    genres = []
    
    # ПАРСЕР PROJECT GUTENBERG
    if "gutenberg.org" in url:
        bibrec_table = soup.find('table', class_='bibrec')
        if bibrec_table:
            for tr in bibrec_table.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if th and td:
                    header = th.get_text(strip=True).lower()
                    # В зависимости от заголовка извлекаем нужные данные
                    if header == 'title': # Название книги
                        title = td.get_text(separator=' ', strip=True).replace('\n', ' ')
                    elif header == 'author': # Автор
                        a_tag = td.find('a')
                        raw_author = a_tag.get_text(strip=True) if a_tag else td.get_text(strip=True)
                        parts = [p.strip() for p in raw_author.split(',')]
                        author = f"{parts[1]} {parts[0]}" if len(parts) >= 2 and not any(char.isdigit() for char in parts[1]) else parts[0]
                    elif header == 'language': # Язык
                        language = tr.get('content', td.get_text(strip=True))
                    elif header == 'release date': # Год публикации
                        match = re.search(r'\d{4}', td.get_text())
                        if match: year = int(match.group())
                    elif header == 'subject': # Жанры
                        a_tag = td.find('a')
                        raw_subject = a_tag.get_text(strip=True) if a_tag else td.get_text(strip=True)
                        genre = raw_subject.split('--')[0].strip().rstrip('.')
                        if genre and not any(char.isdigit() for char in genre):
                            genres.append(genre)

        # Описание (из блока summary-text-container, если есть)
        summary_container = soup.find('div', class_='summary-text-container')
        if summary_container:
            for label in summary_container.find_all('label'):
                label.decompose()
            for input_tag in summary_container.find_all('input'):
                input_tag.decompose()
            clean_desc = summary_container.get_text(separator=' ', strip=True).replace("(This is an automatically generated summary.)", "").strip()
            if clean_desc: description = clean_desc

    # ПАРСЕР STANDARD EBOOKS
    elif "standardebooks.org" in url:
        # Название книги
        title_tag = soup.find('h1', attrs={'property': 'schema:name'})
        if title_tag:
            title = title_tag.get_text(strip=True)
            
        # Автор
        author_tag = soup.find(attrs={'property': 'schema:author'})
        if author_tag:
            author_span = author_tag.find('span', attrs={'property': 'schema:name'})
            if author_span:
                author = author_span.get_text(strip=True)
            else:
                author = author_tag.get_text(strip=True)
                
        # Описание
        desc_section = soup.find('section', id='description')
        if desc_section:
            # Уничтожаем заголовок <h2>, а также все блоки-баннеры с донатами (<aside>, <div>)
            for unwanted in desc_section.find_all(['h2', 'aside', 'div', 'form', 'button']):
                unwanted.decompose()
            description = desc_section.get_text(separator=' ', strip=True)
            
        # Год публикации (из скрытого мета-тега)
        year_meta = soup.find('meta', attrs={'property': 'schema:datePublished'})
        if year_meta and year_meta.get('content'):
            match = re.search(r'\d{4}', year_meta.get('content'))
            if match:
                year = int(match.group())
                
        # Язык (из скрытого мета-тега)
        lang_meta = soup.find('meta', attrs={'property': 'schema:inLanguage'})
        if lang_meta and lang_meta.get('content'):
            language = lang_meta.get('content')
            
        # Жанры
        tags_ul = soup.find('ul', class_='tags')
        if tags_ul:
            for li in tags_ul.find_all('li'):
                genres.append(li.get_text(strip=True))

    # ОБЩАЯ НОРМАЛИЗАЦИЯ ДАННЫХ
    
    LANG_MAP = {
        'en': 'English',
        'ru': 'Russian',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'it': 'Italian',
        'nl': 'Dutch',
        'pt': 'Portuguese',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'fi': 'Finnish'
    }
    
    if language:
        raw_lang = language.lower().strip()
        base_lang = raw_lang.split('-')[0]
        if base_lang in LANG_MAP:
            language = LANG_MAP[base_lang]
        else:
            language = raw_lang.capitalize()[:10]
    else:
        language = "English"
    
    if not genres:
        genres = ["Classic Literature"]
    else:
        cleaned_genres = []
        seen = set()
        for g in genres:
            clean_g = re.sub(r'\s+', ' ', g).strip().title()
            if clean_g and len(clean_g) > 2 and clean_g.lower() not in seen:
                seen.add(clean_g.lower())
                cleaned_genres.append(clean_g)
        genres = cleaned_genres[:3]
        if not genres: genres = ["Classic Literature"]

    if description:
        description = re.sub(r'\s+', ' ', description).strip()
        if len(description) > 1000:
            description = description[:997] + "..."

    return {
        "bcid": f"parsed-{uuid.uuid4().hex[:8]}",
        "title": title[:100],
        "author": author[:100],
        "publication_year": year,
        "isbn": isbn,
        "description": description,
        "language": language[:10],
        "genres": genres,
        "url": url
    }