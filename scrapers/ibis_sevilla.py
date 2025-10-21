"""
Scraper para IBIS Sevilla: https://www.ibis-sevilla.es/es/ofertas-empleo/
HTML sencillo: extrae título, fecha límite (si aparece), enlace y centro.
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IbisSevillaScraper:
    def __init__(self):
        self.base_url = "https://www.ibis-sevilla.es"
        self.empleo_url = "https://www.ibis-sevilla.es/es/ofertas-empleo/"
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

        # 1) localizar listado de ofertas y seguir enlaces a detalle
        # filtramos enlaces relevantes por texto y por url
        anchors = soup.find_all('a', href=True)
        candidate_links: List[str] = []
        for a in anchors:
            text = (a.get_text() or '').strip()
            href = a['href']
            if not text:
                continue
            # palabras clave típicas y evitar menús genéricos
            if any(k in text.lower() for k in ['convocatoria', 'oferta', 'empleo', 'plaza']):
                # ignorar anclas vacías o navegación
                if any(bad in text.lower() for bad in ['inicio', 'contacto', 'aviso', 'política', 'cookies']):
                    continue
                url_abs = href if href.startswith('http') else urljoin(self.base_url, href)
                # filtrar solo páginas de detalle dentro de "ofertas-de-empleo-ibis" (evitar índices)
                if '/ofertas-de-empleo-ibis/' in url_abs:
                    # excluir el índice genérico
                    if url_abs.rstrip('/') in [
                        f"{self.base_url}/es/ofertas-empleo/ofertas-de-empleo-ibis",
                        f"{self.base_url}/es/ofertas-empleo/ofertas-de-empleo-ibis/",
                        f"{self.base_url}/es/ofertas-empleo/",
                    ]:
                        continue
                    if text.lower() in ['ofertas de empleo']:
                        continue
                    if url_abs not in candidate_links:
                        candidate_links.append(url_abs)

        # 2) Visitar detalles y extraer sólo ofertas abiertas
        for link in candidate_links[:40]:  # límite de seguridad
            det = self._parse_detail(link)
            if det:
                ofertas.append(det)

        # deduplicar por título
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
        # cargar detalle
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            if r.encoding == 'ISO-8859-1':
                r.encoding = 'utf-8'
            s = BeautifulSoup(r.text, 'html.parser')
        except requests.RequestException:
            return None

        oferta = {
            'iis': 'IBIS_Sevilla',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Sevilla',
            'categoria': '',
            'titulacion': '',
            'centro': 'IBIS Sevilla',
            'enlace': url
        }

        # Título principal del detalle
        for sel in ['h1', '.entry-title', '.title', 'h2']:
            t = s.select_one(sel)
            if t and t.get_text(strip=True):
                oferta['titulo'] = t.get_text(strip=True)
                break
        if not oferta['titulo']:
            oferta['titulo'] = s.get_text(" ", strip=True)[:120]

        # Fechas desde contenido
        text = s.get_text(" ", strip=True)
        dates = DateParser.extract_dates_from_text(text)
        if dates:
            # supuesto: primera fecha = desde, última = hasta
            dates_sorted = sorted(dates, key=lambda x: x[1])
            oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])

        # Estado por palabras
        low = text.lower()
        if any(w in low for w in ['abierta', 'publicada', 'vigente']):
            oferta['estado'] = 'Abierta'
        elif any(w in low for w in ['cerrada', 'finalizada']):
            oferta['estado'] = 'Cerrada'

        # Filtrar si claramente cerrada
        if oferta['estado'] == 'Cerrada':
            return None
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None

        return oferta if len(oferta['titulo']) >= 5 else None


def test_ibis_sevilla():
    print('Probando scraper IBIS Sevilla...')
    s = IbisSevillaScraper()
    ofertas = s.scrape()
    if not ofertas:
        print('Sin ofertas')
        return ofertas
    print('OFERTAS - IBIS Sevilla')
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
    test_ibis_sevilla()


