import re
import httpx
from fastapi import APIRouter, Depends, HTTPException
from ..oauth2 import get_current_user

router = APIRouter(prefix='/books/isbn', tags=['ISBN lookup'])

def normalize_isbn(raw):
    value = raw.replace('-', '').replace(' ', '').upper()
    if re.fullmatch(r'\d{9}[\dX]', value):
        valid = sum((10-i)*(10 if c == 'X' else int(c)) for i,c in enumerate(value)) % 11 == 0
    elif re.fullmatch(r'97[89]\d{10}', value):
        valid = sum(int(c)*(1 if i % 2 == 0 else 3) for i,c in enumerate(value)) % 10 == 0
    else:
        valid = False
    if not valid:
        raise HTTPException(422, 'Enter a valid ISBN-10 or ISBN-13')
    return value

@router.get('/{isbn}')
def lookup(isbn: str, user=Depends(get_current_user)):
    value = normalize_isbn(isbn)
    try:
        response = httpx.get('https://openlibrary.org/api/books', params={'bibkeys': f'ISBN:{value}', 'format': 'json', 'jscmd': 'data'}, timeout=10, follow_redirects=True)
        response.raise_for_status()
        data = response.json().get(f'ISBN:{value}')
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'ISBN lookup is unavailable. You can still enter details manually.')
    if not data:
        raise HTTPException(404, 'No match found. You can enter details manually.')
    year = re.search(r'\b(\d{4})\b', data.get('publish_date', ''))
    return {'name': data.get('title', ''), 'author': ', '.join(a['name'] for a in data.get('authors', [])),
            'isbn': value, 'publication_year': int(year.group(1)) if year else None,
            'cover_url': data.get('cover', {}).get('medium', ''),
            'source': 'Open Library'}
