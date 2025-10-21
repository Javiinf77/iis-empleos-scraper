"""
Scraper para IBS Granada: https://www.ibsgranada.es/ofertas/
HTML sencillo: extrae título, fechas, enlace.
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IbsGranadaScraper:
    def __init__(self):
        self.base_url = "https://www.ibsgranada.es"
        self.empleo_url = "https://www.ibsgranada.es/ofertas/"
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

        # Estructura actual: listado de <article class="job_list_item">
        items = soup.select('article.job_list_item')
        for it in items:
            status_el = it.select_one('span.status')
            status_classes = status_el.get('class', []) if status_el else []
            # filtrar sólo abiertas
            if not status_el or ('open' not in status_classes):
                continue

            title_el = it.find('h3')
            titulo = title_el.get_text(strip=True) if title_el else ''
            link = ''
            a = title_el.find('a', href=True) if title_el else None
            if a:
                href = a['href']
                link = href if href.startswith('http') else urljoin(self.base_url, href)

            # rango de fechas en p.range tipo "16 Oct. 2025 - 26 Oct. 2025"
            rango_el = it.select_one('p.range')
            fecha_ini = ''
            fecha_fin = ''
            if rango_el:
                rango = rango_el.get_text(strip=True)
                rangon = rango.replace('.', '')  # quitar puntos tras abreviaturas
                parts = [p.strip() for p in rangon.split('-')]
                if len(parts) == 2:
                    d1 = DateParser.parse_date(parts[0])
                    d2 = DateParser.parse_date(parts[1])
                    if d1:
                        fecha_ini = DateParser.format_date_for_display(d1)
                    if d2:
                        fecha_fin = DateParser.format_date_for_display(d2)

            oferta = {
                'iis': 'IBS_Granada',
                'titulo': titulo,
                'fecha_inicio': fecha_ini,
                'fecha_limite': fecha_fin,
                'estado': 'Abierta',
                'provincia': 'Granada',
                'categoria': '',
                'titulacion': '',
                'centro': 'ibs.GRANADA',
                'enlace': link
            }

            # aplicar filtro de fecha fin si existe
            if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                continue

            if len(oferta['titulo']) >= 3:
                ofertas.append(oferta)

        # Deduplicar por enlace o (titulo, enlace)
        seen = set()
        unique: List[Dict] = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('enlace','').strip().lower())
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
            'iis': 'IBS_Granada',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Granada',
            'categoria': '',
            'titulacion': '',
            'centro': 'ibs.GRANADA',
            'enlace': url
        }

        # título detalle
        for sel in ['h1', '.entry-title', 'h2', '.title']:
            t = s.select_one(sel)
            if t and t.get_text(strip=True):
                oferta['titulo'] = t.get_text(strip=True)
                break
        if not oferta['titulo']:
            oferta['titulo'] = s.get_text(" ", strip=True)[:120]

        text = s.get_text(" ", strip=True)
        dates = DateParser.extract_dates_from_text(text)
        if dates:
            dates_sorted = sorted(dates, key=lambda x: x[1])
            oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])

        low = text.lower()
        if any(w in low for w in ['abierta', 'vigente', 'plazo abierto']):
            oferta['estado'] = 'Abierta'
        elif any(w in low for w in ['cerrada', 'finalizada', 'plazo cerrado']):
            oferta['estado'] = 'Cerrada'

        return oferta if len(oferta['titulo']) >= 5 else None

    def _parse_element(self, el) -> Optional[Dict]:
        oferta = {
            'iis': 'IBS_Granada',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Granada',
            'categoria': '',
            'titulacion': '',
            'centro': 'ibs.GRANADA',
            'enlace': ''
        }

        for sel in ['h1', 'h2', 'h3', 'h4', '.title', '.titulo', 'a']:
            t = el.find(sel)
            if t and t.get_text(strip=True):
                oferta['titulo'] = t.get_text(strip=True)
                break
        if not oferta['titulo']:
            text = el.get_text(" ", strip=True)
            if not text:
                return None
            oferta['titulo'] = text[:120]

        a = el.find('a', href=True)
        if a:
            href = a['href']
            oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)

        text = el.get_text(" ", strip=True)
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


def test_ibs_granada():
    print('Probando scraper IBS Granada...')
    s = IbsGranadaScraper()
    ofertas = s.scrape()
    if not ofertas:
        print('Sin ofertas')
        return ofertas
    print('OFERTAS - IBS Granada')
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
    test_ibs_granada()


