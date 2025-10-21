"""
Script principal para el web scraping de ofertas de empleo de Institutos de Investigación Sanitaria (IIS).
"""

import json
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Any
import requests
from bs4 import BeautifulSoup

# Importar utilidades
from utils.date_parser import DateParser


class IISJobScraper:
    """Clase principal para gestionar el scraping de ofertas de empleo de IIS."""
    
    def __init__(self, config_path: str = "config/webs.json"):
        """
        Inicializa el scraper con la configuración.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.session = requests.Session()
        self._setup_session()
        
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo JSON."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo de configuración {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error al parsear el archivo de configuración: {e}")
            sys.exit(1)
    
    def _setup_session(self):
        """Configura la sesión de requests con headers y configuración."""
        config = self.config.get('configuracion', {})
        
        headers = {
            'User-Agent': config.get('user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session.headers.update(headers)
        self.session.timeout = config.get('timeout', 30)
    
    def get_page_content(self, url: str) -> BeautifulSoup:
        """
        Obtiene el contenido HTML de una URL.
        
        Args:
            url: URL a consultar
            
        Returns:
            Objeto BeautifulSoup con el contenido parseado
        """
        try:
            print(f"Consultando: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            # Intentar detectar la codificación
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener {url}: {e}")
            return None
    
    async def run_scraper(self, iis_name: str = None) -> Dict[str, List[Dict]]:
        """
        Ejecuta el scraping para uno o todos los IIS.
        
        Args:
            iis_name: Nombre específico del IIS a procesar (opcional)
            
        Returns:
            Diccionario con los resultados del scraping
        """
        results = {}
        iis_list = self.config.get('iis_webs', [])
        
        # Filtrar por IIS específico si se proporciona
        if iis_name:
            iis_list = [iis for iis in iis_list if iis['nombre'].lower() == iis_name.lower()]
        
        # Solo procesar IIS activos
        active_iis = [iis for iis in iis_list if iis.get('activo', True)]
        
        print(f"Procesando {len(active_iis)} IIS activos...")
        
        for iis in active_iis:
            nombre = iis['nombre']
            url = iis['url']
            tipo = iis['tipo']
            
            print(f"\n{'='*50}")
            print(f"Procesando {nombre} ({tipo})")
            print(f"URL: {url}")
            print(f"{'='*50}")
            
            try:
                # Obtener contenido de la página
                soup = self.get_page_content(url)
                if soup is None:
                    results[nombre] = []
                    continue
                
                # Procesar según el tipo de página
                ofertas = await self._process_page_by_type(soup, tipo, nombre, url)
                results[nombre] = ofertas
                
                # Mostrar ofertas directamente
                print(f"\n{nombre.upper()}")
                print("-" * (len(nombre) + 4))
                
                if not ofertas:
                    print("Sin ofertas abiertas")
                else:
                    for oferta in ofertas:
                        centro = oferta.get('centro') or 'Centro no especificado'
                        titulo = oferta.get('titulo') or 'Sin título'
                        f_ini = oferta.get('fecha_inicio') or '-'
                        f_fin = oferta.get('fecha_limite') or '-'
                        enlace = oferta.get('enlace') or '-'
                        print(f"{centro} - {titulo} | Inicio: {f_ini} | Límite: {f_fin} | Link: {enlace}")
                
                # Delay entre requests
                delay = self.config.get('configuracion', {}).get('delay_entre_requests', 2)
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"Error procesando {nombre}: {e}")
                results[nombre] = []
        
        return results
    
    async def _process_page_by_type(self, soup: BeautifulSoup, tipo: str, nombre: str, url: str) -> List[Dict]:
        """
        Procesa una página según su tipo usando scrapers específicos.
        
        Args:
            soup: Objeto BeautifulSoup con el contenido
            tipo: Tipo de página (html_simple, fundanet, personio, etc.)
            nombre: Nombre del IIS
            url: URL de la página
            
        Returns:
            Lista de ofertas encontradas
        """
        ofertas = []
        
        # Usar scrapers específicos si están disponibles
        try:
            if nombre == 'CIBERISCIII':
                from scrapers.ciberisciii import CiberisciiiPlaywrightScraper
                scraper = CiberisciiiPlaywrightScraper()
                ofertas = await scraper.scrape_ofertas()
            elif nombre == 'FIMABIS':
                from scrapers.fimabis import FimabisScraper
                scraper = FimabisScraper()
                ofertas = scraper.scrape_ofertas()
            elif nombre == 'IGTP':
                from scrapers.igtp import IgtpScraper
                scraper = IgtpScraper()
                ofertas = scraper.scrape_ofertas()
            elif nombre == 'IBIS_Sevilla':
                from scrapers.ibis_sevilla import IbisSevillaScraper
                ofertas = IbisSevillaScraper().scrape()
            elif nombre == 'IBS_Granada':
                from scrapers.ibs_granada import IbsGranadaScraper
                ofertas = IbsGranadaScraper().scrape()
            elif nombre == 'IBSAL':
                from scrapers.ibsal import IbsalScraper
                ofertas = IbsalScraper().scrape()
            elif nombre == 'IMIB':
                from scrapers.imib import ImibScraper
                scraper = ImibScraper()
                ofertas = scraper.scrape_ofertas()
            elif nombre == 'IDIVAL':
                from scrapers.idival import IdivalScraper
                scraper = IdivalScraper()
                ofertas = scraper.scrape_ofertas()
            else:
                # Fallback a métodos genéricos
                if tipo == 'html_simple':
                    ofertas = self._scrape_html_simple(soup, nombre, url)
                elif tipo == 'fundanet':
                    ofertas = self._scrape_fundanet(soup, nombre, url)
                elif tipo == 'personio':
                    ofertas = self._scrape_personio(soup, nombre, url)
                elif tipo == 'jsf':
                    ofertas = self._scrape_jsf(soup, nombre, url)
                elif tipo == 'html_dinamico':
                    ofertas = self._scrape_html_dinamico(soup, nombre, url)
                else:
                    print(f"Tipo de página no soportado: {tipo}")
        except ImportError as e:
            print(f"Error importando scraper para {nombre}: {e}")
            # Fallback a métodos genéricos
            if tipo == 'html_simple':
                ofertas = self._scrape_html_simple(soup, nombre, url)
            elif tipo == 'fundanet':
                ofertas = self._scrape_fundanet(soup, nombre, url)
            elif tipo == 'personio':
                ofertas = self._scrape_personio(soup, nombre, url)
            elif tipo == 'jsf':
                ofertas = self._scrape_jsf(soup, nombre, url)
            elif tipo == 'html_dinamico':
                ofertas = self._scrape_html_dinamico(soup, nombre, url)
        except Exception as e:
            print(f"Error ejecutando scraper para {nombre}: {e}")
            # Fallback a métodos genéricos
            if tipo == 'html_simple':
                ofertas = self._scrape_html_simple(soup, nombre, url)
            elif tipo == 'fundanet':
                ofertas = self._scrape_fundanet(soup, nombre, url)
            elif tipo == 'personio':
                ofertas = self._scrape_personio(soup, nombre, url)
            elif tipo == 'jsf':
                ofertas = self._scrape_jsf(soup, nombre, url)
            elif tipo == 'html_dinamico':
                ofertas = self._scrape_html_dinamico(soup, nombre, url)
        
        return ofertas
    
    def _scrape_html_simple(self, soup: BeautifulSoup, nombre: str, url: str) -> List[Dict]:
        """Scraper genérico para páginas HTML simples."""
        ofertas = []
        
        # Buscar elementos comunes que contengan ofertas
        selectors = [
            '.oferta', '.convocatoria', '.plazo-abierto', '.job-item',
            '.employment', '.vacancy', '.position', '.announcement'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Encontrados {len(elements)} elementos con selector '{selector}'")
                break
        
        if not elements:
            # Buscar enlaces que contengan palabras clave
            keywords = ['empleo', 'trabajo', 'convocatoria', 'oferta', 'vacante']
            for keyword in keywords:
                links = soup.find_all('a', href=True, string=lambda text: text and keyword.lower() in text.lower())
                if links:
                    elements = links
                    print(f"Encontrados {len(elements)} enlaces con palabra clave '{keyword}'")
                    break
        
        for element in elements:
            oferta = self._extract_oferta_info(element, nombre, url)
            if oferta:
                ofertas.append(oferta)
        
        return ofertas
    
    def _scrape_fundanet(self, soup: BeautifulSoup, nombre: str, url: str) -> List[Dict]:
        """Scraper específico para páginas tipo Fundanet."""
        ofertas = []
        
        # Buscar tablas o listas de convocatorias
        tables = soup.find_all('table')
        lists = soup.find_all(['ul', 'ol'])
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    oferta = self._extract_oferta_from_row(cells, nombre, url)
                    if oferta:
                        ofertas.append(oferta)
        
        for list_elem in lists:
            items = list_elem.find_all('li')
            for item in items:
                oferta = self._extract_oferta_info(item, nombre, url)
                if oferta:
                    ofertas.append(oferta)
        
        return ofertas
    
    def _scrape_personio(self, soup: BeautifulSoup, nombre: str, url: str) -> List[Dict]:
        """Scraper específico para portales Personio."""
        ofertas = []
        
        # Buscar elementos típicos de Personio
        job_elements = soup.select('a.job-list-item, .job-item, .position-item')
        
        for element in job_elements:
            oferta = self._extract_oferta_info(element, nombre, url)
            if oferta:
                ofertas.append(oferta)
        
        return ofertas
    
    def _scrape_jsf(self, soup: BeautifulSoup, nombre: str, url: str) -> List[Dict]:
        """Scraper para páginas JSF (JavaServer Faces)."""
        ofertas = []
        
        # JSF suele generar IDs específicos
        jsf_elements = soup.find_all(id=lambda x: x and ('oferta' in x.lower() or 'convocatoria' in x.lower()))
        
        for element in jsf_elements:
            oferta = self._extract_oferta_info(element, nombre, url)
            if oferta:
                ofertas.append(oferta)
        
        return ofertas
    
    def _scrape_html_dinamico(self, soup: BeautifulSoup, nombre: str, url: str) -> List[Dict]:
        """Scraper para páginas HTML dinámicas."""
        ofertas = []
        
        # Buscar elementos con JavaScript o contenido dinámico
        dynamic_elements = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['dynamic', 'ajax', 'content', 'list']
        ))
        
        for element in dynamic_elements:
            oferta = self._extract_oferta_info(element, nombre, url)
            if oferta:
                ofertas.append(oferta)
        
        return ofertas
    
    def _extract_oferta_info(self, element, nombre: str, base_url: str) -> Dict:
        """
        Extrae información de una oferta desde un elemento HTML.
        
        Args:
            element: Elemento BeautifulSoup
            nombre: Nombre del IIS
            base_url: URL base para enlaces relativos
            
        Returns:
            Diccionario con la información de la oferta
        """
        oferta = {
            'iis': nombre,
            'titulo': '',
            'fecha_limite': '',
            'enlace': '',
            'descripcion': ''
        }
        
        # Extraer título
        title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.titulo', 'a']
        for selector in title_selectors:
            title_elem = element.find(selector)
            if title_elem and title_elem.get_text(strip=True):
                oferta['titulo'] = title_elem.get_text(strip=True)
                break
        
        # Si no se encontró título, usar el texto del elemento
        if not oferta['titulo']:
            oferta['titulo'] = element.get_text(strip=True)[:100] + '...' if len(element.get_text(strip=True)) > 100 else element.get_text(strip=True)
        
        # Extraer enlace
        link_elem = element.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                oferta['enlace'] = href
            else:
                # Construir URL absoluta
                from urllib.parse import urljoin
                oferta['enlace'] = urljoin(base_url, href)
        
        # Extraer fecha límite
        text = element.get_text()
        dates_found = DateParser.extract_dates_from_text(text)
        if dates_found:
            # Usar la fecha más reciente encontrada
            latest_date = max(dates_found, key=lambda x: x[1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(latest_date[1])
        
        # Filtrar ofertas cerradas
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        # Filtrar elementos sin título o con texto muy corto
        if len(oferta['titulo']) < 5:
            return None
        
        return oferta
    
    def _extract_oferta_from_row(self, cells, nombre: str, base_url: str) -> Dict:
        """Extrae información de oferta desde una fila de tabla."""
        oferta = {
            'iis': nombre,
            'titulo': '',
            'fecha_limite': '',
            'enlace': '',
            'descripcion': ''
        }
        
        # Asumir que el título está en la primera celda
        if cells:
            oferta['titulo'] = cells[0].get_text(strip=True)
            
            # Buscar enlaces en la primera celda
            link = cells[0].find('a', href=True)
            if link:
                href = link['href']
                if href.startswith('http'):
                    oferta['enlace'] = href
                else:
                    from urllib.parse import urljoin
                    oferta['enlace'] = urljoin(base_url, href)
        
        # Buscar fecha en las celdas restantes
        for cell in cells[1:]:
            text = cell.get_text()
            dates_found = DateParser.extract_dates_from_text(text)
            if dates_found:
                latest_date = max(dates_found, key=lambda x: x[1])
                oferta['fecha_limite'] = DateParser.format_date_for_display(latest_date[1])
                break
        
        # Filtrar ofertas cerradas
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        return oferta if oferta['titulo'] else None
    
    


def main():
    """Función principal del script."""
    print("Iniciando scraper de ofertas de empleo IIS...")
    
    # Crear instancia del scraper
    # Asegurar ruta relativa correcta
    scraper = IISJobScraper(config_path=os.path.join('iisempleos','config','webs.json') if not os.path.exists('config/webs.json') else 'config/webs.json')
    
    # Verificar argumentos de línea de comandos
    iis_especifico = None
    if len(sys.argv) > 1:
        iis_especifico = sys.argv[1]
        print(f"Procesando IIS específico: {iis_especifico}")
    
    # Ejecutar scraping
    import asyncio
    results = asyncio.run(scraper.run_scraper(iis_especifico))
    
    # Mostrar total
    total_ofertas = sum(len(ofertas) for ofertas in results.values())
    print(f"\nTOTAL: {total_ofertas} ofertas")
    print("="*80)
    
    print("\nScraping completado!")


if __name__ == "__main__":
    main()
