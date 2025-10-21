"""
Scraper específico para CIBERISCIII usando Playwright para contenido dinámico
"""

import asyncio
from typing import List, Dict, Optional
import sys
import os

# Playwright para contenido dinámico
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Añadir el directorio padre al path para importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class CiberisciiiPlaywrightScraper:
    """Scraper específico para CIBERISCIII usando Playwright."""
    
    def __init__(self):
        self.empleo_url = "https://www.ciberisciii.es/empleo"
    
    async def scrape_ofertas(self) -> List[Dict]:
        """
        Extrae las ofertas de empleo de CIBERISCIII usando Playwright.
        
        Returns:
            Lista de diccionarios con la información de las ofertas
        """
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        ofertas = []
        
        
        async with async_playwright() as p:
            # Lanzar navegador
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navegar a la página
                await page.goto(self.empleo_url, wait_until='networkidle')
                
                # Esperar a que se carguen las ofertas
                await asyncio.sleep(5)
                
                # Buscar ofertas en las tres secciones
                # 1) Empleo general con paginación (hay múltiples páginas)
                ofertas.extend(await self._extract_general_paginated(page))
                ofertas.extend(await self._extract_ofertas_section(page, "divOfertasEmpleoReposicion", "Tasa de reposición"))
                ofertas.extend(await self._extract_ofertas_section(page, "divOfertasEmpleoEstabilizacion", "Tasa de estabilización"))
                
            except Exception as e:
                pass
            finally:
                await browser.close()
        
        # Eliminar duplicados
        ofertas = self._remove_duplicates(ofertas)
        
        return ofertas
    
    async def _extract_ofertas_section(self, page, div_id: str, tipo: str) -> List[Dict]:
        """
        Extrae ofertas de una sección específica.
        
        Args:
            page: Página de Playwright
            div_id: ID del div que contiene las ofertas
            tipo: Tipo de oferta
            
        Returns:
            Lista de ofertas encontradas
        """
        ofertas = []
        
        try:
            # Buscar el div que contiene las ofertas
            div_element = await page.query_selector(f"#{div_id}")
            
            if div_element:
                # Buscar filas de la tabla
                rows = await div_element.query_selector_all("tr")
                
                for i, row in enumerate(rows[1:], 1):  # Saltar la cabecera
                    try:
                        cells = await row.query_selector_all("td")
                        
                        if len(cells) >= 10:  # Verificar que tiene todas las columnas
                            oferta = await self._parse_row(cells, tipo)
                            if oferta:
                                ofertas.append(oferta)
                        elif len(cells) >= 5:  # Intentar con menos columnas
                            oferta = await self._parse_row_flexible(cells, tipo)
                            if oferta:
                                ofertas.append(oferta)
                    except Exception as e:
                        continue
                
        except Exception as e:
            pass
        
        return ofertas

    async def _extract_general_paginated(self, page) -> List[Dict]:
        """Extrae ofertas de 'Empleo general' paginando (paginador inferior)."""
        ofertas: List[Dict] = []
        # Primer volcado de la página 1
        ofertas.extend(await self._extract_ofertas_section(page, "divOfertasEmpleo", "Empleo general"))

        # Localizar paginador y, si existe, ir a la página 2 (como mínimo)
        try:
            paginador = await page.query_selector("#divpaginado, #divpaginadoReposicion, nav ul.pagination")
            if paginador:
                # Buscar enlace a 'Siguiente' o a la página '2'
                # Preferimos enlace con número 2 dentro del paginador general
                btn_2 = await paginador.query_selector("li >> text=2")
                if not btn_2:
                    btn_2 = await page.query_selector("nav ul.pagination li >> text=2")
                if btn_2:
                    await btn_2.click()
                    # Esperar a que recargue la tabla
                    await page.wait_for_timeout(1200)
                    # Re-extraer tabla de empleo general (Ahora página 2)
                    ofertas.extend(await self._extract_ofertas_section(page, "divOfertasEmpleo", "Empleo general"))
                else:
                    # Intentar botón 'Siguiente'
                    btn_next = await paginador.query_selector("li >> text=Siguiente")
                    if btn_next:
                        await btn_next.click()
                        await page.wait_for_timeout(1200)
                        ofertas.extend(await self._extract_ofertas_section(page, "divOfertasEmpleo", "Empleo general"))
        except Exception:
            pass

        return ofertas
    
    async def _parse_row(self, cells, tipo: str) -> Optional[Dict]:
        """
        Parsea una fila de la tabla.
        
        Args:
            cells: Lista de celdas de la fila
            tipo: Tipo de oferta
            
        Returns:
            Diccionario con la información de la oferta o None
        """
        oferta = {
            'iis': 'CIBERISCIII',
            'area': '',
            'titulo': '',
            'fecha_limite': '',
            'fecha_inicio': '',
            'enlace': '',
            'descripcion': '',
            'estado': '',
            'tipo_plaza': tipo,
            'centro': '',
            'provincia': '',
            'categoria': '',
            'titulacion': ''
        }
        
        try:
            # Estructura de la tabla: Área | Convocatoria | Desde | Hasta | Estado | Provincia | Categoría | Titulación | Centro | Detalle
            if len(cells) >= 10:
                oferta['area'] = (await cells[0].text_content() or '')
                oferta['titulo'] = await cells[1].text_content() or ''  # Convocatoria
                oferta['fecha_inicio'] = await cells[2].text_content() or ''  # Desde
                oferta['fecha_limite'] = await cells[3].text_content() or ''  # Hasta
                oferta['estado'] = await cells[4].text_content() or ''  # Estado
                oferta['provincia'] = await cells[5].text_content() or ''  # Provincia
                oferta['categoria'] = await cells[6].text_content() or ''  # Categoría
                oferta['titulacion'] = await cells[7].text_content() or ''  # Titulación
                oferta['centro'] = await cells[8].text_content() or ''  # Centro
                
                # Buscar enlace en la última celda
                try:
                    link = await cells[9].query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            oferta['enlace'] = href
                except:
                    pass
                
                # Limpiar texto
                for key in ['area','titulo', 'fecha_inicio', 'fecha_limite', 'estado', 'provincia', 'categoria', 'titulacion', 'centro']:
                    oferta[key] = oferta[key].strip()
                
                # Filtrar ofertas cerradas
                if oferta['estado'] and oferta['estado'].lower() not in ['abierta', 'publicada']:
                    return None
                
                # Filtrar ofertas con fechas límite pasadas
                if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                    return None
                
                # Filtrar elementos sin título válido (aceptar "UT" como válido)
                if len(oferta['titulo']) < 2:
                    return None
                
                return oferta
                
        except Exception as e:
            pass
        
        return None
    
    async def _parse_row_flexible(self, cells, tipo: str) -> Optional[Dict]:
        """
        Parsea una fila con estructura flexible.
        
        Args:
            cells: Lista de celdas de la fila
            tipo: Tipo de oferta
            
        Returns:
            Diccionario con la información de la oferta o None
        """
        oferta = {
            'iis': 'CIBERISCIII',
            'area': '',
            'titulo': '',
            'fecha_limite': '',
            'fecha_inicio': '',
            'enlace': '',
            'descripcion': '',
            'estado': '',
            'tipo_plaza': tipo,
            'centro': '',
            'provincia': '',
            'categoria': '',
            'titulacion': ''
        }
        
        try:
            # Intentar diferentes estructuras
            if len(cells) >= 9:
                # Reposición: Área | Convocatoria | Desde | Hasta | Estado | Provincia | Categoría | Titulación | Detalle
                oferta['area'] = (await cells[0].text_content() or '').strip()
                oferta['titulo'] = (await cells[1].text_content() or '').strip()
                oferta['fecha_inicio'] = (await cells[2].text_content() or '').strip()
                oferta['fecha_limite'] = (await cells[3].text_content() or '').strip()
                oferta['estado'] = (await cells[4].text_content() or '').strip()
                oferta['provincia'] = (await cells[5].text_content() or '').strip()
                oferta['categoria'] = (await cells[6].text_content() or '').strip()
                oferta['titulacion'] = (await cells[7].text_content() or '').strip()

                # enlace en celda 8
                try:
                    link = await cells[8].query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            oferta['enlace'] = href
                except:
                    pass

                # Filtrado
                if oferta['estado'] and oferta['estado'].lower() not in ['abierta', 'publicada']:
                    return None
                if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                    return None
                if len(oferta['titulo']) < 2:
                    return None
                return oferta

            if len(cells) >= 5:
                # Buscar el patrón de ID de oferta (ej: 3238/3707)
                for i, cell in enumerate(cells):
                    text = await cell.text_content() or ''
                    if '/' in text and text.replace('/', '').replace(' ', '').isdigit():
                        oferta['titulo'] = text.strip()
                        break
                
                # Si no encontramos ID, usar la primera celda
                if not oferta['titulo']:
                    oferta['titulo'] = await cells[0].text_content() or ''
                
                # Buscar fechas en las siguientes celdas
                for i in range(1, min(len(cells), 4)):
                    text = await cells[i].text_content() or ''
                    if '/' in text and len(text.split('/')) == 3:
                        if not oferta['fecha_inicio']:
                            oferta['fecha_inicio'] = text.strip()
                        elif not oferta['fecha_limite']:
                            oferta['fecha_limite'] = text.strip()
                            break
                
                # Buscar estado
                for i in range(2, min(len(cells), 6)):
                    text = await cells[i].text_content() or ''
                    if text.lower() in ['publicada', 'abierta', 'cerrada']:
                        oferta['estado'] = text.strip()
                        break
                
                # Buscar provincia
                for i in range(3, min(len(cells), 7)):
                    text = await cells[i].text_content() or ''
                    if text.upper() in ['MADRID', 'BARCELONA', 'SEVILLA', 'ILLES BALEARS', 'VALENCIA']:
                        oferta['provincia'] = text.strip()
                        break
                
                # Buscar enlace
                for cell in cells:
                    try:
                        link = await cell.query_selector("a")
                        if link:
                            href = await link.get_attribute("href")
                            if href:
                                oferta['enlace'] = href
                                break
                    except:
                        pass
                
                # Limpiar texto
                for key in ['area','titulo', 'fecha_inicio', 'fecha_limite', 'estado', 'provincia', 'categoria', 'titulacion', 'centro']:
                    oferta[key] = oferta[key].strip()
                
                # Filtrar ofertas cerradas
                if oferta['estado'] and oferta['estado'].lower() not in ['abierta', 'publicada']:
                    return None
                
                # Filtrar ofertas con fechas límite pasadas
                if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                    return None
                
                # Filtrar elementos sin título válido (aceptar "UT" como válido)
                if len(oferta['titulo']) < 2:
                    return None
                
                return oferta
                
        except Exception as e:
            pass
        
        return None
    
    def _remove_duplicates(self, ofertas: List[Dict]) -> List[Dict]:
        """Elimina ofertas duplicadas basándose en el título."""
        seen_titles = set()
        unique_ofertas = []
        
        for oferta in ofertas:
            title_key = oferta['titulo'].lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_ofertas.append(oferta)
        
        return unique_ofertas
    
    def print_ofertas(self, ofertas: List[Dict]):
        """Imprime las ofertas encontradas de forma organizada."""
        if not ofertas:
            print("❌ No se encontraron ofertas abiertas en CIBERISCIII")
            return
        
        print("\nOFERTAS DE EMPLEO - CIBERISCIII")
        print("-" * 50)
        
        for i, oferta in enumerate(ofertas, 1):
            print(f"{i}. {oferta['titulo']}")
            
            if oferta['fecha_inicio']:
                print(f"   Fecha inicio: {oferta['fecha_inicio']}")
            
            if oferta['fecha_limite']:
                days_left = DateParser.get_days_until_deadline(oferta['fecha_limite'])
                print(f"   Fecha límite: {oferta['fecha_limite']} ({days_left} días restantes)")
            
            if oferta['enlace']:
                print(f"   Enlace: {oferta['enlace']}")
            
            if oferta['estado']:
                print(f"   Estado: {oferta['estado']}")
            
            if oferta['tipo_plaza']:
                print(f"   Tipo: {oferta['tipo_plaza']}")
            
            if oferta['centro']:
                print(f"   Centro: {oferta['centro']}")
            
            if oferta['provincia']:
                print(f"   Provincia: {oferta['provincia']}")
            
            if oferta['categoria']:
                print(f"   Categoría: {oferta['categoria']}")
            
            if oferta['titulacion']:
                print(f"   Titulación: {oferta['titulacion']}")
            
            print()


async def test_ciberisciii_playwright():
    """Función de prueba para el scraper de CIBERISCIII con Playwright."""
    print("Probando scraper de CIBERISCIII con Playwright...")
    
    scraper = CiberisciiiPlaywrightScraper()
    ofertas = await scraper.scrape_ofertas()
    scraper.print_ofertas(ofertas)
    
    return ofertas


def test_ciberisciii():
    """Función de prueba síncrona."""
    return asyncio.run(test_ciberisciii_playwright())


if __name__ == "__main__":
    test_ciberisciii()
