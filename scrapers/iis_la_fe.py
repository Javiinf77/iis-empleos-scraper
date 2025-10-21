"""
Scraper específico para IIS La Fe
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import sys
import os

# Añadir el directorio padre al path para importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IisLaFeScraper:
    """Scraper específico para IIS La Fe."""
    
    def __init__(self):
        self.empleo_url = "https://www.iislafe.es/es/talento/empleo/"
        self.date_parser = DateParser()
    
    def scrape(self) -> List[Dict]:
        """
        Extrae las ofertas de empleo de IIS La Fe.
        
        Returns:
            Lista de diccionarios con la información de las ofertas
        """
        ofertas = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Primero obtener la primera página para detectar el número total de páginas
            response = requests.get(self.empleo_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Detectar número de páginas desde la paginación
            max_pages = 1
            pagination = soup.select_one('.pagination')
            if pagination:
                page_links = pagination.find_all('a', href=True)
                for link in page_links:
                    try:
                        page_num = int(link.get_text(strip=True))
                        max_pages = max(max_pages, page_num)
                    except ValueError:
                        continue
            
            print(f"IIS La Fe: Detectadas {max_pages} páginas")
            
            # Procesar solo las primeras 3 páginas
            for page in range(1, min(4, max_pages + 1)):
                if page == 1:
                    # Ya tenemos la primera página
                    page_soup = soup
                else:
                    # Obtener página específica
                    page_url = f"{self.empleo_url}?page={page}"
                    page_response = requests.get(page_url, headers=headers, timeout=30)
                    page_response.raise_for_status()
                    page_soup = BeautifulSoup(page_response.content, 'html.parser')
                
                # Buscar ofertas en esta página
                page_ofertas = self._scrape_page(page_soup, page)
                ofertas.extend(page_ofertas)
                
                print(f"  Página {page}: {len(page_ofertas)} ofertas")
            
        except Exception as e:
            print(f"Error scraping IIS La Fe: {e}")
        
        return ofertas
    
    def _scrape_page(self, soup: BeautifulSoup, page_num: int) -> List[Dict]:
        """Extrae ofertas de una página específica."""
        ofertas = []
        
        # Buscar divs con clase "empleo-item" que contengan status abierto
        empleo_items = soup.find_all('div', class_='empleo-item')
        
        for item in empleo_items:
            # Verificar si tiene status "Abierta"
            status_span = item.find('span', class_='status status--open')
            if status_span and 'abierta' in status_span.get_text().lower():
                # Buscar el primer enlace de oferta (no el de inscripción)
                oferta_link = item.find('a', href=True, string=lambda text: text and any(
                    keyword in text.lower() for keyword in ['contratación', 'técnico', 'investigador', 'personal']
                ))
                
                if oferta_link:
                    oferta = self._extract_oferta_info(oferta_link)
                    if oferta and self._is_valid_oferta(oferta):
                        ofertas.append(oferta)
        
        return ofertas
    
    def _is_oferta_abierta(self, link_element) -> bool:
        """Verifica si una oferta está abierta basándose en el contexto del elemento."""
        # Buscar el texto "Abierta" en el contexto del elemento
        parent = link_element.parent
        if parent:
            parent_text = parent.get_text().lower()
            if 'abierta' in parent_text:
                return True
        
        # Buscar en elementos hermanos
        siblings = link_element.find_next_siblings()
        for sibling in siblings:
            sibling_text = sibling.get_text().lower()
            if 'abierta' in sibling_text:
                return True
        
        # Buscar en elementos anteriores
        previous_siblings = link_element.find_previous_siblings()
        for sibling in previous_siblings:
            sibling_text = sibling.get_text().lower()
            if 'abierta' in sibling_text:
                return True
        
        return False
    
    def _extract_oferta_info(self, element) -> Dict:
        """Extrae información de una oferta desde un elemento HTML."""
        oferta = {
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'enlace': '',
            'centro': 'IIS La Fe',
            'descripcion': ''
        }
        
        # El elemento ya es un enlace, extraer información directamente
        if element.name == 'a' and 'href' in element.attrs:
            href = element['href']
            if href.startswith('http'):
                oferta['enlace'] = href
            else:
                oferta['enlace'] = f"https://www.iislafe.es{href}"
            
            # Extraer título del texto del enlace
            titulo = element.get_text(strip=True)
            if titulo and len(titulo) > 10:
                oferta['titulo'] = titulo
        
        # Buscar fechas en el contexto del elemento (div empleo-item)
        parent = element.parent
        if parent and parent.name == 'div' and 'empleo-item' in parent.get('class', []):
            context_text = parent.get_text()
            dates_found = self.date_parser.extract_dates_from_text(context_text)
            if dates_found:
                # Usar la fecha más reciente como fecha límite
                latest_date = max(dates_found, key=lambda x: x[1])
                oferta['fecha_limite'] = self.date_parser.format_date_for_display(latest_date[1])
        
        return oferta
    
    def _is_valid_oferta(self, oferta: Dict) -> bool:
        """Valida si una oferta es válida y está abierta."""
        # Debe tener título y enlace
        if not oferta['titulo'] or len(oferta['titulo']) < 15:
            return False
        
        if not oferta['enlace'] or not oferta['enlace'].startswith('http'):
            return False
        
        # Debe ser un enlace a una oferta específica
        if '/es/talento/empleo/' not in oferta['enlace']:
            return False
        
        return True


if __name__ == '__main__':
    scraper = IisLaFeScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
