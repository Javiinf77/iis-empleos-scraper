"""
Scraper para IDIVAL: https://www.idival.org/empleo/
La página puede tener SSL estricto y contenido dinámico. Usamos requests con verify=False
y BeautifulSoup para listas simples; si falla, se puede adaptar a Playwright.
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
import urllib3
import asyncio
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser

try:
    from playwright.async_api import async_playwright
    PW = True
except ImportError:
    PW = False

class IdivalScraper:
    def __init__(self):
        self.base_url = "https://www.idival.org"
        self.url = "https://www.idival.org/empleo/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def fetch(self) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(self.url, timeout=30, verify=False)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except requests.RequestException as e:
            return None

    def scrape_ofertas(self) -> List[Dict]:
        # 0) Intento Playwright directo (navegar a "Convocatorias Abiertas")
        if PW:
            try:
                return asyncio.run(self._scrape_playwright())
            except RuntimeError:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._scrape_playwright())

        soup = self.fetch()
        if not soup:
            return []

        # 1) Buscar enlace a "Convocatorias Abiertas"
        abierto_link = None
        for a in soup.find_all('a', href=True):
            text = (a.get_text() or '').strip().lower()
            href = a['href']
            if 'abierta' in text or 'abiertas' in text:
                abierto_link = href
                break
            if any(k in href.lower() for k in ['abierta', 'abiertas', 'estado=a', 'convocatorias']):
                abierto_link = href
                break
        if abierto_link and not abierto_link.startswith('http'):
            abierto_link = urljoin(self.base_url, abierto_link)

        # 2) Si apunta a Fundanet/IFundanet o a listados propios, procesar esa página
        ofertas: List[Dict] = []
        if abierto_link:
            ofertas = self._scrape_fundanet_like(abierto_link)
            if ofertas:
                return ofertas

        # 3) Fallback: intentar parsear bloques/entradas en la misma página
        items = soup.select('article, .job, .convocatoria, .oferta, .list-group-item') or soup.find_all('a', href=True)
        for el in items:
            of = self._parse_item(el)
            if of:
                if of.get('fecha_limite') and not DateParser.is_date_open(of['fecha_limite']):
                    continue
                ofertas.append(of)

        # deduplicar
        seen = set()
        uniq = []
        for of in ofertas:
            key = (of.get('titulo','').strip().lower(), of.get('enlace',''))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(of)
        return uniq

    def _scrape_fundanet_like(self, url: str) -> List[Dict]:
        try:
            r = self.session.get(url, timeout=30, verify=False)
            r.raise_for_status()
        except requests.RequestException:
            return []
        s = BeautifulSoup(r.text, 'html.parser')
        ofertas: List[Dict] = []

        # Buscar tablas con columnas típicas o filas con estado
        tables = s.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                row_text = ' '.join(td.get_text(' ', strip=True) for td in cells)
                estado = row_text.lower()
                if 'abierta' not in estado and 'publicada' not in estado:
                    continue
                titulo = cells[0].get_text(strip=True)
                fecha_ini = ''
                fecha_fin = ''
                fechas = DateParser.extract_dates_from_text(row_text)
                if fechas:
                    fechas_sorted = sorted(fechas, key=lambda x: x[1])
                    fecha_ini = DateParser.format_date_for_display(fechas_sorted[0][1])
                    fecha_fin = DateParser.format_date_for_display(fechas_sorted[-1][1])
                    if fecha_fin and not DateParser.is_date_open(fecha_fin):
                        continue
                enlace = ''
                a = cells[-1].find('a', href=True) or cells[0].find('a', href=True)
                if a:
                    href = a['href']
                    enlace = href if href.startswith('http') else urljoin(url, href)
                if len(titulo) >= 3:
                    ofertas.append({
                        'iis': 'IDIVAL',
                        'titulo': titulo,
                        'fecha_inicio': fecha_ini,
                        'fecha_limite': fecha_fin,
                        'estado': 'Abierta',
                        'provincia': 'Cantabria',
                        'categoria': '',
                        'titulacion': '',
                        'centro': 'IDIVAL',
                        'enlace': enlace
                    })

        # Si no hubo tablas, intentar tarjetas/enlaces con texto
        if not ofertas:
            cards = s.select('article, .oferta, .convocatoria, .card, .list-group-item') or s.find_all('a', href=True)
            for el in cards:
                text = el.get_text(' ', strip=True)
                if not text:
                    continue
                if 'abiert' not in text.lower():
                    continue
                fechas = DateParser.extract_dates_from_text(text)
                fecha_fin = ''
                fecha_ini = ''
                if fechas:
                    fechas_sorted = sorted(fechas, key=lambda x: x[1])
                    fecha_ini = DateParser.format_date_for_display(fechas_sorted[0][1])
                    fecha_fin = DateParser.format_date_for_display(fechas_sorted[-1][1])
                    if fecha_fin and not DateParser.is_date_open(fecha_fin):
                        continue
                a = el.find('a', href=True) if hasattr(el, 'find') else None
                enlace = ''
                if a:
                    href = a['href']
                    enlace = href if href.startswith('http') else urljoin(url, href)
                ofertas.append({
                    'iis': 'IDIVAL',
                    'titulo': text[:200],
                    'fecha_inicio': fecha_ini,
                    'fecha_limite': fecha_fin,
                    'estado': 'Abierta',
                    'provincia': 'Cantabria',
                    'categoria': '',
                    'titulacion': '',
                    'centro': 'IDIVAL',
                    'enlace': enlace or url
                })

        return ofertas

    async def _scrape_playwright(self) -> List[Dict]:
        ofertas: List[Dict] = []
        if not PW:
            return ofertas
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(self.url, wait_until='networkidle')
                await page.wait_for_timeout(1200)
                # Click en "Convocatorias Abiertas"
                for sel in ["text=Convocatorias Abiertas", "text=Abiertas", "text=OPEN", "role=button[name='Convocatorias Abiertas']"]:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        # Esperar a que cambie el contenido
                        await page.wait_for_timeout(800)
                        await page.wait_for_load_state('networkidle')
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(800)
                        break

                # En algunos sitios abre en misma SPA o redirige a Fundanet
                # Intentar detectar tablas con ofertas
                rows = []
                # reintentos para que JS pinte la tabla
                for _ in range(6):
                    rows = await page.query_selector_all('table tbody tr')
                    if rows:
                        break
                    await page.wait_for_timeout(700)
                if not rows:
                    # probar dentro de iframes (Fundanet suele ir en iframe)
                    for fr in page.frames:
                        rows = await fr.query_selector_all('table tbody tr')
                        if rows:
                            page = fr
                            break

                for row in rows:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 3:
                        continue
                    row_texts = [((await c.text_content()) or '').strip() for c in cells]
                    estado_txt = ' '.join(row_texts).lower()
                    if ('abierta' not in estado_txt) and ('publicada' not in estado_txt):
                        continue
                    titulo = row_texts[0]
                    fecha_ini = ''
                    fecha_fin = ''
                    fechas = DateParser.extract_dates_from_text(' '.join(row_texts))
                    if fechas:
                        fechas_sorted = sorted(fechas, key=lambda x: x[1])
                        fecha_ini = DateParser.format_date_for_display(fechas_sorted[0][1])
                        fecha_fin = DateParser.format_date_for_display(fechas_sorted[-1][1])
                        if fecha_fin and not DateParser.is_date_open(fecha_fin):
                            continue
                    enlace = ''
                    link = await row.query_selector('a[href]')
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            enlace = href
                    if len(titulo) >= 3:
                        ofertas.append({
                            'iis': 'IDIVAL',
                            'titulo': titulo,
                            'fecha_inicio': fecha_ini,
                            'fecha_limite': fecha_fin,
                            'estado': 'Abierta',
                            'provincia': 'Cantabria',
                            'categoria': '',
                            'titulacion': '',
                            'centro': 'IDIVAL',
                            'enlace': enlace
                        })
            finally:
                await browser.close()
        # Dedup
        seen = set()
        res: List[Dict] = []
        for of in ofertas:
            key = (of.get('titulo','').lower(), of.get('enlace',''))
            if key in seen:
                continue
            seen.add(key)
            res.append(of)
        return res

    def _parse_item(self, el) -> Optional[Dict]:
        oferta = {
            'iis': 'IDIVAL',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Cantabria',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIVAL',
            'enlace': ''
        }

        # título
        title = None
        for sel in ['h1','h2','h3','h4','.title','.entry-title','a']:
            title = el.find(sel) if hasattr(el, 'find') else None
            if title and title.get_text(strip=True):
                oferta['titulo'] = title.get_text(strip=True)
                a = title.find('a', href=True)
                if a:
                    href = a['href']
                    oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)
                break
        if not oferta['titulo']:
            text = el.get_text(" ", strip=True) if hasattr(el, 'get_text') else str(el)
            if not text:
                return None
            oferta['titulo'] = text[:120]
            if hasattr(el, 'get') and el.get('href'):
                href = el.get('href')
                oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)

        # fechas
        text = el.get_text(" ", strip=True) if hasattr(el, 'get_text') else ''
        dates = DateParser.extract_dates_from_text(text)
        if dates:
            ds = sorted(dates, key=lambda x: x[1])
            oferta['fecha_inicio'] = DateParser.format_date_for_display(ds[0][1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(ds[-1][1])

        low = text.lower()
        if any(w in low for w in ['abierta','publicada','vigente']):
            oferta['estado'] = 'Abierta'
        elif any(w in low for w in ['cerrada','finalizada']):
            oferta['estado'] = 'Cerrada'

        return oferta if len(oferta['titulo']) >= 5 else None


if __name__ == '__main__':
    s = IdivalScraper()
    ofertas = s.scrape_ofertas()
    print('OFERTAS - IDIVAL')
    print('-' * 50)
    if not ofertas:
        print('Sin ofertas abiertas ahora mismo')
    else:
        for i, of in enumerate(ofertas, 1):
            print(f"{i}. {of['titulo']}")
            if of.get('fecha_limite'):
                print(f"   Fecha límite: {of['fecha_limite']}")
            if of.get('enlace'):
                print(f"   Enlace: {of['enlace']}")


