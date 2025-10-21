"""
Scraper para Puerta de Hierro: https://investigacionpuertadehierro.com/empleo-y-formacion/
HTML con tabla de ofertas con estado "Abierta" o "Cerrada"
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class PuertaHierroScraper:
    def __init__(self):
        self.base_url = "https://investigacionpuertadehierro.com"
        self.empleo_url = "https://investigacionpuertadehierro.com/empleo-y-formacion/"
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

        # Buscar tabla con ofertas
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Al menos cabecera + 1 fila
                continue
            
            # Procesar filas (saltar cabecera)
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 6:  # Mínimo: Ref, Título, Convocatoria, F.Inicio, F.Fin, Estado
                    continue
                
                oferta = self._parse_row(cells)
                if oferta:
                    ofertas.append(oferta)

        # Deduplicar
        seen = set()
        unique = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('referencia',''))
            if key in seen:
                continue
            seen.add(key)
            unique.append(of)

        return unique

    def _parse_row(self, cells) -> Optional[Dict]:
        oferta = {
            'iis': 'Puerta_Hierro',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Madrid',
            'categoria': '',
            'titulacion': '',
            'centro': 'Hospital Universitario Puerta de Hierro-Majadahonda',
            'enlace': '',
            'referencia': ''
        }

        try:
            # Estructura esperada: Referencia | Título | Convocatoria | F.Inicio | F.Fin | Estado | Resolución
            if len(cells) >= 7:
                oferta['referencia'] = cells[0].get_text(strip=True)
                oferta['titulo'] = cells[1].get_text(strip=True)
                
                # Fecha inicio (celda 3)
                fecha_inicio_text = cells[3].get_text(strip=True)
                fecha_inicio = DateParser.parse_date(fecha_inicio_text)
                if fecha_inicio:
                    oferta['fecha_inicio'] = DateParser.format_date_for_display(fecha_inicio)
                
                # Fecha límite (celda 4)
                fecha_fin_text = cells[4].get_text(strip=True)
                fecha_fin = DateParser.parse_date(fecha_fin_text)
                if fecha_fin:
                    oferta['fecha_limite'] = DateParser.format_date_for_display(fecha_fin)
                
                # Estado (celda 5)
                estado_text = cells[5].get_text(strip=True)
                oferta['estado'] = estado_text
                
                # Enlace en columna Convocatoria (celda 2)
                link_elem = cells[2].find('a', href=True)
                if link_elem:
                    href = link_elem['href']
                    oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)
                
            elif len(cells) >= 5:
                # Estructura mínima: Ref | Título | F.Inicio | F.Fin | Estado
                oferta['referencia'] = cells[0].get_text(strip=True)
                oferta['titulo'] = cells[1].get_text(strip=True)
                
                fecha_inicio_text = cells[2].get_text(strip=True)
                fecha_inicio = DateParser.parse_date(fecha_inicio_text)
                if fecha_inicio:
                    oferta['fecha_inicio'] = DateParser.format_date_for_display(fecha_inicio)
                
                fecha_fin_text = cells[3].get_text(strip=True)
                fecha_fin = DateParser.parse_date(fecha_fin_text)
                if fecha_fin:
                    oferta['fecha_limite'] = DateParser.format_date_for_display(fecha_fin)
                
                estado_text = cells[4].get_text(strip=True)
                oferta['estado'] = estado_text

        except Exception:
            return None

        # Filtrar solo ofertas abiertas
        if oferta['estado'].lower() not in ['abierta', 'abierto', 'open']:
            return None
        
        # Filtrar por fecha límite
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        # Filtrar convocatorias que no son ofertas de empleo
        title_lower = oferta['titulo'].lower()
        if any(word in title_lower for word in [
            'ayudas para la intensificación',
            'intensificación de la actividad investigadora',
            'ayudas 2025',
            'convocatoria de ayudas',
            'intensificación investigadora',
            'profesionales sanitarios',
            'becas',
            'subvenciones'
        ]):
            return None

        return oferta


if __name__ == '__main__':
    scraper = PuertaHierroScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
