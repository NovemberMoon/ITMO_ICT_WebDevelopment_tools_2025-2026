"""
Модуль извлечения метаданных о книгах из HTML-страниц.

Обеспечивает парсинг для поддерживаемых источников (Project Gutenberg, Standard Ebooks)
с последующей нормализацией данных для приведения к единой схеме ответа API.
"""

import uuid
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class BookData:
    """
    Строгая структура для хранения извлеченных метаданных о книге.
    Обеспечивает типизацию и безопасную инициализацию значений по умолчанию.
    """
    source_url: str
    bcid: str
    title: str = ""
    author: str = "Unknown"
    publication_year: int = 0
    language: str = ""
    genres: List[str] = field(default_factory=list)
    description: str = ""


def _normalize_metadata(book: BookData) -> BookData:
    """
    Очищает и нормализует извлеченные метаданные о книге.

    Заполняет отсутствующие поля значениями по умолчанию и ограничивает 
    длину строковых полей для соответствия спецификации ответа.

    Args:
        book (BookData): Экземпляр структуры данных с извлеченной информацией.

    Returns:
        BookData: Тот же экземпляр с нормализованными метаданными.
    """
    lang_map = {
        'en': 'English', 'ru': 'Russian', 'fr': 'French', 
        'de': 'German', 'es': 'Spanish', 'it': 'Italian'
    }
    
    if book.language:
        base_lang = book.language.lower().strip().split('-')[0]
        book.language = lang_map.get(base_lang, book.language.capitalize()[:10])
    else:
        book.language = "Unknown"
    
    cleaned_genres = []
    seen = set()
    for g in book.genres:
        clean_g = re.sub(r'\s+', ' ', g).strip().title()
        if clean_g and len(clean_g) > 2 and clean_g.lower() not in seen:
            seen.add(clean_g.lower())
            cleaned_genres.append(clean_g)
    book.genres = cleaned_genres[:3]

    if book.description:
        description = re.sub(r'\s+', ' ', book.description).strip()
        book.description = description[:997] + "..." if len(description) > 1000 else description

    book.title = book.title.strip()[:100]
    book.author = book.author.strip()[:100]
    
    return book


def _parse_gutenberg(soup: BeautifulSoup, url: str) -> BookData:
    """
    Извлекает метаданные книги из HTML-дерева сайта Project Gutenberg.

    Args:
        soup (BeautifulSoup): Разобранное HTML-дерево страницы.
        url (str): Исходный URL-адрес страницы.

    Returns:
        BookData: Структура с извлеченными данными.
    """
    book = BookData(source_url=url, bcid=uuid.uuid4().hex[:12])

    bibrec_table = soup.find('table', class_='bibrec')
    if bibrec_table:
        for tr in bibrec_table.find_all('tr'):
            th, td = tr.find('th'), tr.find('td')
            if not (th and td): 
                continue
                
            header = th.get_text(strip=True).lower()
            if header == 'title':
                book.title = td.get_text(separator=' ', strip=True).replace('\n', ' ')
            elif header == 'author':
                a_tag = td.find('a')
                raw_author = a_tag.get_text(strip=True) if a_tag else td.get_text(strip=True)
                parts = [p.strip() for p in raw_author.split(',')]
                book.author = f"{parts[1]} {parts[0]}" if len(parts) >= 2 and not any(char.isdigit() for char in parts[1]) else parts[0]
            elif header == 'language':
                book.language = tr.get('content', td.get_text(strip=True))
            elif header == 'release date':
                match = re.search(r'\d{4}', td.get_text())
                if match: 
                    book.publication_year = int(match.group())
            elif header == 'subject':
                a_tag = td.find('a')
                raw_subject = a_tag.get_text(strip=True) if a_tag else td.get_text(strip=True)
                genre = raw_subject.split('--')[0].strip().rstrip('.')
                if genre and not any(char.isdigit() for char in genre):
                    book.genres.append(genre)

    summary_container = soup.find('div', class_='summary-text-container')
    if summary_container:
        for tag in summary_container.find_all(['label', 'input']): 
            tag.decompose()
        clean_desc = summary_container.get_text(separator=' ', strip=True).replace("(This is an automatically generated summary.)", "").strip()
        if clean_desc: 
            book.description = clean_desc

    return book


def _parse_standardebooks(soup: BeautifulSoup, url: str) -> BookData:
    """
    Извлекает метаданные книги из HTML-дерева сайта Standard Ebooks.

    Args:
        soup (BeautifulSoup): Разобранное HTML-дерево страницы.
        url (str): Исходный URL-адрес страницы.

    Returns:
        BookData: Структура с извлеченными данными.
    """
    book = BookData(source_url=url, bcid=uuid.uuid4().hex[:12])

    title_tag = soup.find('h1', attrs={'property': 'schema:name'})
    if title_tag: 
        book.title = title_tag.get_text(strip=True)
        
    author_tag = soup.find(attrs={'property': 'schema:author'})
    if author_tag:
        author_span = author_tag.find('span', attrs={'property': 'schema:name'})
        book.author = author_span.get_text(strip=True) if author_span else author_tag.get_text(strip=True)
            
    desc_section = soup.find('section', id='description')
    if desc_section:
        for unwanted in desc_section.find_all(['h2', 'aside', 'div', 'form', 'button']): 
            unwanted.decompose()
        book.description = desc_section.get_text(separator=' ', strip=True)
        
    year_meta = soup.find('meta', attrs={'property': 'schema:datePublished'})
    if year_meta and year_meta.get('content'):
        match = re.search(r'\d{4}', year_meta.get('content'))
        if match: 
            book.publication_year = int(match.group())
            
    lang_meta = soup.find('meta', attrs={'property': 'schema:inLanguage'})
    if lang_meta and lang_meta.get('content'):
        book.language = lang_meta.get('content')
        
    tags_ul = soup.find('ul', class_='tags')
    if tags_ul:
        book.genres = [li.get_text(strip=True) for li in tags_ul.find_all('li')]

    return book


def extract_book_info(html: str, url: str) -> Dict[str, Any]:
    """
    Главная функция извлечения данных.

    Определяет подходящий адаптер на основе исходного URL, инициирует парсинг
    и передает полученную структуру на этап нормализации. В конце сериализует 
    объект обратно в словарь для передачи по HTTP.

    Args:
        html (str): Сырой HTML-код веб-страницы.
        url (str): Исходный URL-адрес страницы.

    Returns:
        Dict[str, Any]: Словарь с нормализованными метаданными книги.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    if "gutenberg.org" in url:
        parsed_book = _parse_gutenberg(soup, url)
    elif "standardebooks.org" in url:
        parsed_book = _parse_standardebooks(soup, url)
    else:
        parsed_book = BookData(source_url=url, bcid=uuid.uuid4().hex[:12])

    normalized_book = _normalize_metadata(parsed_book)
    
    return asdict(normalized_book)