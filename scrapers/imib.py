"""
Scraper para IMIB (JSF dinámico): https://www.imib.es/rrhh/ofertasDeEmpleo.jsf
Usamos Playwright para renderizar y leer la tabla de ofertas abiertas.
"""

import sys
import os
import asyncio
from typing import List, Dict

import requests
import urllib3
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class ImibScraper:
    def __init__(self):
        self.url = "https://www.imib.es/rrhh/ofertasDeEmpleo.jsf"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })
        # Suprimir warnings de certificado al usar verify=False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    async def scrape_async(self) -> List[Dict]:
        if not PLAYWRIGHT_AVAILABLE:
            return []

        ofertas: List[Dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(self.url, wait_until='networkidle')
                # Dar tiempo a JSF/PrimeFaces para poblar la tabla
                await page.wait_for_timeout(3500)
                # Desplegar contenido perezoso
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(800)
                except Exception:
                    pass

                # Intentar activar pestañas/botones de empleo
                for selector in ["text=Empleo", "text=Ofertas", "text=RRHH", "text=Trabaja", "text=Plazo"]:
                    try:
                        el = await page.query_selector(selector)
                        if el:
                            await el.click()
                            await page.wait_for_timeout(1000)
                    except Exception:
                        continue
                # Intentar esperar a filas de tabla
                try:
                    await page.wait_for_selector('table tbody tr', timeout=3000)
                except Exception:
                    pass

                tbl = await page.query_selector("table, .ui-datatable-tablewrapper table")
                if tbl:
                    rows = await page.query_selector_all("table tbody tr")
                    for idx, row in enumerate(rows, 1):
                        cells = await row.query_selector_all("td")
                        if len(cells) < 2:
                            continue
                        # columnas típicas: Título | Fecha | Estado | Detalle
                        titulo = (await cells[0].text_content() or '').strip()
                        fecha = (await cells[1].text_content() or '').strip()
                        estado = (await cells[2].text_content() or '').strip().lower() if len(cells) >= 3 else ''
                        enlace = ''
                        link = await cells[0].query_selector('a')
                        if link:
                            href = await link.get_attribute('href')
                            if href:
                                enlace = href
                        if 'cerrad' in estado:
                            continue
                        fecha_lim = ''
                        if fecha:
                            dates = DateParser.extract_dates_from_text(fecha)
                            if dates:
                                fecha_lim = DateParser.format_date_for_display(max(dates, key=lambda x: x[1])[1])
                                if fecha_lim and not DateParser.is_date_open(fecha_lim):
                                    continue
                        if len(titulo) < 3:
                            continue
                        ofertas.append({
                            'iis': 'IMIB',
                            'titulo': titulo,
                            'fecha_inicio': '',
                            'fecha_limite': fecha_lim,
                            'estado': 'Abierta' if 'abiert' in estado or not estado else 'Publicada',
                            'provincia': '',
                            'categoria': '',
                            'titulacion': '',
                            'centro': 'IMIB',
                            'enlace': enlace
                        })
                else:
                    # Buscar dentro de iframes
                    try:
                        frames = page.frames
                    except Exception:
                        frames = []
                    for fr in frames:
                        try:
                            rows = await fr.query_selector_all("table tbody tr")
                            for row in rows:
                                cells = await row.query_selector_all('td')
                                if len(cells) < 2:
                                    continue
                                titulo = (await cells[0].text_content() or '').strip()
                                fecha = (await cells[1].text_content() or '').strip()
                                estado = (await cells[2].text_content() or '').strip().lower() if len(cells) >= 3 else ''
                                enlace = ''
                                link = await cells[0].query_selector('a')
                                if link:
                                    href = await link.get_attribute('href')
                                    if href:
                                        enlace = href
                                if 'cerrad' in estado:
                                    continue
                                fecha_lim = ''
                                if fecha:
                                    dates = DateParser.extract_dates_from_text(fecha)
                                    if dates:
                                        fecha_lim = DateParser.format_date_for_display(max(dates, key=lambda x: x[1])[1])
                                        if fecha_lim and not DateParser.is_date_open(fecha_lim):
                                            continue
                                if len(titulo) >= 3:
                                    ofertas.append({
                                        'iis': 'IMIB',
                                        'titulo': titulo,
                                        'fecha_inicio': '',
                                        'fecha_limite': fecha_lim,
                                        'estado': 'Abierta' if 'abiert' in estado or not estado else 'Publicada',
                                        'provincia': 'Murcia',
                                        'categoria': '',
                                        'titulacion': '',
                                        'centro': 'IMIB',
                                        'enlace': enlace
                                    })
                        except Exception:
                            continue

                    # Fallback: seguir posibles enlaces de ofertas y parsear detalle
                    links = await page.query_selector_all('a[href]')
                    seen = set()
                    for a in links:
                        href = await a.get_attribute('href')
                        text = (await a.text_content() or '').strip()
                        if not href or href in seen:
                            continue
                        seen.add(href)
                        if any(k in (href.lower() + ' ' + text.lower()) for k in ['oferta', 'empleo', 'convocatoria', 'rrhh']):
                            page2 = await context.new_page()
                            try:
                                await page2.goto(href if href.startswith('http') else self.url.rsplit('/',1)[0] + '/' + href, wait_until='load')
                                await page2.wait_for_timeout(1200)
                                content = await page2.text_content('body')
                                if not content:
                                    continue
                                if 'cerrad' in content.lower():
                                    continue
                                # título
                                tnode = await page2.query_selector('h1, h2, .title, .entry-title')
                                titulo = (await tnode.text_content() or '').strip() if tnode else (text or href)
                                fechas = DateParser.extract_dates_from_text(content)
                                fecha_lim = ''
                                if fechas:
                                    fecha_lim = DateParser.format_date_for_display(max(fechas, key=lambda x: x[1])[1])
                                    if fecha_lim and not DateParser.is_date_open(fecha_lim):
                                        continue
                                ofertas.append({
                                    'iis': 'IMIB',
                                    'titulo': titulo,
                                    'fecha_inicio': '',
                                    'fecha_limite': fecha_lim,
                                    'estado': 'Abierta',
                                    'provincia': '',
                                    'categoria': '',
                                    'titulacion': '',
                                    'centro': 'IMIB',
                                    'enlace': await page2.url
                                })
                            finally:
                                await page2.close()

                    # Fallback final basado en texto: buscar bloques IMIBxx_Cyy con estado y fechas
                    try:
                        body_text = await page.text_content('body')
                    except Exception:
                        body_text = ''
                    if body_text:
                        import re
                        # normalizar espacios
                        body_norm = ' '.join(body_text.split())
                        for m in re.finditer(r"\(IMIB\d+_C\d+\)", body_norm):
                            start = max(0, m.start() - 300)
                            end = min(len(body_norm), m.end() + 600)
                            snippet = body_norm[start:end]
                            snippet_clean = ' '.join(snippet.split())
                            # Estado
                            if 'abierto' not in snippet_clean.lower() and 'abierta' not in snippet_clean.lower():
                                continue
                            # Fechas
                            fechas = DateParser.extract_dates_from_text(snippet_clean)
                            fecha_ini = ''
                            fecha_lim = ''
                            if fechas:
                                fechas_sorted = sorted(fechas, key=lambda x: x[1])
                                fecha_ini = DateParser.format_date_for_display(fechas_sorted[0][1])
                                fecha_lim = DateParser.format_date_for_display(fechas_sorted[-1][1])
                                if fecha_lim and not DateParser.is_date_open(fecha_lim):
                                    continue
                            # Título: tomar inicio del párrafo desde "Resolución" hasta el código
                            title_start = snippet_clean.lower().find('resoluci')
                            if title_start == -1:
                                title_start = 0
                            title_end = snippet_clean.find(')', m.start() - start) + 1
                            titulo = snippet_clean[title_start:title_end]
                            if len(titulo) < 15:
                                titulo = snippet_clean[:180]
                            ofertas.append({
                                'iis': 'IMIB',
                                'titulo': titulo.strip(),
                                'fecha_inicio': fecha_ini,
                                'fecha_limite': fecha_lim,
                                'estado': 'Abierta',
                                'provincia': 'Murcia',
                                'categoria': '',
                                'titulacion': '',
                                'centro': 'IMIB',
                                'enlace': self.url
                            })
            finally:
                await browser.close()

        return ofertas

    def scrape(self) -> List[Dict]:
        # 1) Intento por requests al HTML fuente (view-source)
        ofertas = self._scrape_requests()
        if ofertas:
            return ofertas
        # 2) Fallback a Playwright
        try:
            return asyncio.run(self.scrape_async())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.scrape_async())

    def _scrape_requests(self) -> List[Dict]:
        try:
            resp = self.session.get(self.url, timeout=30, verify=False)
            resp.raise_for_status()
        except requests.RequestException:
            return []

        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(" ", strip=True)

        ofertas: List[Dict] = []

        # Patrón por bloques con IMIBxx_Cyy
        import re
        text_norm = ' '.join(text.split())
        for m in re.finditer(r"\(IMIB\d+_C\d+\)", text_norm):
            start = max(0, m.start() - 300)
            end = min(len(text_norm), m.end() + 600)
            snippet = text_norm[start:end]
            low = snippet.lower()
            if 'abierto' not in low and 'abierta' not in low:
                continue
            fechas = DateParser.extract_dates_from_text(snippet)
            fecha_ini = ''
            fecha_fin = ''
            if fechas:
                fechas_sorted = sorted(fechas, key=lambda x: x[1])
                fecha_ini = DateParser.format_date_for_display(fechas_sorted[0][1])
                fecha_fin = DateParser.format_date_for_display(fechas_sorted[-1][1])
                if fecha_fin and not DateParser.is_date_open(fecha_fin):
                    continue
            # título
            title_start = snippet.lower().find('resoluci')
            if title_start == -1:
                title_start = 0
            title_end = snippet.find(')', 0) + 1
            titulo = snippet[title_start:title_end].strip()[:220]
            if len(titulo) < 20:
                titulo = snippet[:220]
            ofertas.append({
                'iis': 'IMIB',
                'titulo': titulo,
                'fecha_inicio': fecha_ini,
                'fecha_limite': fecha_fin,
                'estado': 'Abierta',
                'provincia': 'Murcia',
                'categoria': '',
                'titulacion': '',
                'centro': 'IMIB',
                'enlace': self.url
            })

        return ofertas


if __name__ == '__main__':
    s = ImibScraper()
    ofertas = s.scrape_ofertas()
    print('OFERTAS - IMIB')
    print('-' * 50)
    for i, of in enumerate(ofertas, 1):
        print(f"{i}. {of['titulo']}")
        if of.get('fecha_limite'):
            print(f"   Fecha límite: {of['fecha_limite']}")
        if of.get('enlace'):
            print(f"   Enlace: {of['enlace']}")


