"""
Scraper para IDIBAPS: https://www.clinicbarcelona.org/idibaps/trabajar-idibaps/ofertas-de-trabajo
Tabla dinámica con pestañas de ofertas abiertas y cerradas
"""

import sys
import os
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IdibapsScraper:
    def __init__(self):
        self.base_url = "https://www.clinicbarcelona.org"
        self.empleo_url = "https://www.clinicbarcelona.org/idibaps/trabajar-idibaps/ofertas-de-trabajo"
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

    async def scrape_async(self) -> List[Dict]:
        if not PLAYWRIGHT_AVAILABLE:
            return self.scrape_requests()

        ofertas: List[Dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(self.empleo_url, wait_until='networkidle')
                await page.wait_for_timeout(2000)

                # Buscar pestañas o botones para ofertas abiertas
                tab_selectors = [
                    "text=Abiertas",
                    "text=Activas", 
                    "text=Open",
                    "text=Disponibles",
                    "text=Vacantes",
                    "text=Ofertas",
                    "[data-tab*='abierta']",
                    "[data-tab*='open']",
                    "[data-tab*='active']",
                    ".tab[data-tab*='abierta']",
                    ".tab[data-tab*='open']",
                    ".tab[data-tab*='active']",
                    "button:has-text('Abiertas')",
                    "button:has-text('Activas')",
                    "button:has-text('Open')"
                ]

                for selector in tab_selectors:
                    try:
                        tab = await page.query_selector(selector)
                        if tab:
                            await tab.click()
                            await page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue
                
                # Intentar hacer scroll para cargar contenido dinámico
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

                # Buscar elementos li con la clase específica de ofertas de investigación
                offer_elements = await page.query_selector_all('li.research-offer-list_item.u-wrapper')
                
                if not offer_elements:
                    # Fallback: buscar cualquier li que contenga "research-offer"
                    offer_elements = await page.query_selector_all('li[class*="research-offer"]')
                
                for li_element in offer_elements:
                    oferta = await self._parse_li_element(li_element)
                    if oferta:
                        ofertas.append(oferta)

            finally:
                await browser.close()

        # Deduplicar
        seen = set()
        unique = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('enlace',''))
            if key in seen:
                continue
            seen.add(key)
            unique.append(of)

        return unique

    def scrape_requests(self) -> List[Dict]:
        soup = self.fetch()
        if not soup:
            return []

        ofertas: List[Dict] = []

        # Buscar tabla de ofertas
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Procesar filas (saltar cabecera)
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                oferta = self._parse_row(cells)
                if oferta:
                    ofertas.append(oferta)

        # Deduplicar
        seen = set()
        unique = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('enlace',''))
            if key in seen:
                continue
            seen.add(key)
            unique.append(of)

        return unique

    async def _parse_row_playwright(self, cells) -> Optional[Dict]:
        oferta = {
            'iis': 'IDIBAPS',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': 'Abierta',
            'provincia': 'Barcelona',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIBAPS',
            'enlace': ''
        }

        try:
            # Buscar título en las primeras celdas
            for i, cell in enumerate(cells[:3]):
                text = await cell.text_content()
                if text and len(text.strip()) > 10:
                    oferta['titulo'] = text.strip()
                    break
            
            # Buscar enlace
            for cell in cells:
                link = await cell.query_selector('a[href]')
                if link:
                    href = await link.get_attribute('href')
                    if href:
                        oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)
                        break
            
            # Buscar fechas en el texto de todas las celdas
            all_text = ''
            for cell in cells:
                text = await cell.text_content()
                if text:
                    all_text += ' ' + text
            
            dates = DateParser.extract_dates_from_text(all_text)
            if dates:
                dates_sorted = sorted(dates, key=lambda x: x[1])
                oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
                oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])
                
                # Filtrar por fecha límite
                if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                    return None

        except Exception:
            return None

        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        return oferta

    def _parse_row(self, cells) -> Optional[Dict]:
        oferta = {
            'iis': 'IDIBAPS',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': 'Abierta',
            'provincia': 'Barcelona',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIBAPS',
            'enlace': ''
        }

        try:
            # Buscar título en las primeras celdas
            for i, cell in enumerate(cells[:3]):
                text = cell.get_text(strip=True)
                if text and len(text) > 10:
                    oferta['titulo'] = text
                    break
            
            # Buscar enlace
            for cell in cells:
                link = cell.find('a', href=True)
                if link:
                    href = link['href']
                    oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)
                    break
            
            # Buscar fechas en el texto de todas las celdas
            all_text = ''
            for cell in cells:
                text = cell.get_text(strip=True)
                if text:
                    all_text += ' ' + text
            
            dates = DateParser.extract_dates_from_text(all_text)
            if dates:
                dates_sorted = sorted(dates, key=lambda x: x[1])
                oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
                oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])
                
                # Filtrar por fecha límite - solo ofertas con fecha límite futura
                if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                    return None
            else:
                # Si no hay fechas, probablemente no es una oferta válida
                return None

        except Exception:
            return None

        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        return oferta

    async def _parse_li_element(self, li_element) -> Optional[Dict]:
        """Extrae información de un elemento li de oferta de investigación."""
        oferta = {
            'iis': 'IDIBAPS',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': 'Abierta',
            'provincia': 'Barcelona',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIBAPS',
            'enlace': ''
        }

        try:
            # Buscar título en elementos h1, h2, h3, h4, h5, h6 o elementos con clase title
            title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.titulo', '.job-title', 'a']
            for selector in title_selectors:
                title_elem = await li_element.query_selector(selector)
                if title_elem:
                    text = await title_elem.text_content()
                    if text and len(text.strip()) > 10:
                        oferta['titulo'] = text.strip()
                        break
            
            # Si no encontramos título específico, usar el texto del elemento
            if not oferta['titulo']:
                text = await li_element.text_content()
                if text and len(text.strip()) > 10:
                    oferta['titulo'] = text.strip()[:200]  # Limitar longitud
            
            # Buscar enlace
            link_elem = await li_element.query_selector('a[href]')
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)
            
            # Buscar fechas en el texto del elemento
            text = await li_element.text_content()
            if text:
                dates = DateParser.extract_dates_from_text(text)
                if dates:
                    dates_sorted = sorted(dates, key=lambda x: x[1])
                    oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
                    oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])
                    
                    # Filtrar por fecha límite - solo ofertas con fecha límite futura
                    if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                        return None
                else:
                    # Si no hay fechas, probablemente no es una oferta válida
                    return None

        except Exception:
            return None

        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        return oferta

    def scrape(self) -> List[Dict]:
        # Intentar primero con Playwright, luego con requests
        try:
            return asyncio.run(self.scrape_async())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.scrape_async())


def test_idibaps():
    print('Probando scraper IDIBAPS...')
    s = IdibapsScraper()
    ofertas = s.scrape()
    if not ofertas:
        print('Sin ofertas')
        return ofertas
    print('OFERTAS - IDIBAPS')
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
    test_idibaps()
