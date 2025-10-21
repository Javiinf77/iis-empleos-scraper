"""
Scraper para IBSAL: https://ibsal.es/convocatorias-de-empleo/
HTML sencillo (WordPress): extrae listados de ofertas con fecha y enlace.
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IbsalScraper:
    def __init__(self):
        self.base_url = "https://ibsal.es"
        self.empleo_url = "https://ibsal.es/convocatorias-de-empleo/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })

    def fetch(self) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(self.empleo_url, timeout=30)
            resp.raise_for_status()
            if resp.encoding == 'ISO-8859-1':
                resp.encoding = 'utf-8'
            return BeautifulSoup(resp.text, 'html.parser')
        except requests.RequestException:
            return None

    def scrape(self) -> List[Dict]:
        soup = self.fetch()
        if not soup:
            return []

        ofertas: List[Dict] = []

        # En sitios WP suele estar en entries o listados
        selectors = [
            'article', '.entry', '.post', '.list-group-item', 'ul li', '.convocatoria', '.oferta'
        ]

        # Buscar listados visibles y seguir enlaces a detalle específicos de empleo
        anchors = soup.find_all('a', href=True)
        for a in anchors:
            text = (a.get_text() or '').strip()
            href = a['href']
            if not text:
                continue
            url_abs = href if href.startswith('http') else urljoin(self.base_url, href)
            # En IBSAL, las ofertas de empleo están bajo /convocatorias/ref-XX_YYYY-...
            if '/convocatorias/ref-' in url_abs:
                det = self._parse_detail(url_abs)
                if det:
                    ofertas.append(det)

        # deduplicar
        seen = set()
        unique = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('enlace',''))
            if key in seen:
                continue
            seen.add(key)
            unique.append(of)

        return unique

    def _parse_detail(self, url: str) -> Optional[Dict]:
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            if r.encoding == 'ISO-8859-1':
                r.encoding = 'utf-8'
            s = BeautifulSoup(r.text, 'html.parser')
        except requests.RequestException:
            return None
        oferta = {
            'iis': 'IBSAL',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Salamanca',
            'categoria': '',
            'titulacion': '',
            'centro': 'IBSAL',
            'enlace': url
        }

        for sel in ['h1', '.entry-title', 'h2', '.title']:
            t = s.select_one(sel)
            if t and t.get_text(strip=True):
                oferta['titulo'] = t.get_text(strip=True)
                break
        if not oferta['titulo']:
            text = s.get_text(" ", strip=True)
            if not text:
                return None
            oferta['titulo'] = text[:120]

        text = s.get_text(" ", strip=True)
        dates = DateParser.extract_dates_from_text(text)
        if dates:
            dates_sorted = sorted(dates, key=lambda x: x[1])
            oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])

        low = text.lower()
        if any(w in low for w in ['abierta', 'publicada', 'vigente']):
            oferta['estado'] = 'Abierta'
        elif any(w in low for w in ['cerrada', 'finalizada']):
            oferta['estado'] = 'Cerrada'

        if oferta['estado'] == 'Cerrada':
            return None
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None

        return oferta if len(oferta['titulo']) >= 5 else None


def test_ibsal():
    print('Probando scraper IBSAL...')
    s = IbsalScraper()
    ofertas = s.scrape()
    if not ofertas:
        print('Sin ofertas')
        return ofertas
    print('OFERTAS - IBSAL')
    print('-' * 50)
    for i, of in enumerate(ofertas, 1):
        print(f"{i}. {of['titulo']}")
        if of.get('fecha_inicio'):
            print(f"   Fecha inicio: {of['fecha_inicio']}")
        if of.get('fecha_limite'):
            print(f"   Fecha límite: {of['fecha_limite']}")
        if of.get('enlace'):
            print(f"   Enlace: {of['enlace']}")
    return ofertas


if __name__ == '__main__':
    test_ibsal()


