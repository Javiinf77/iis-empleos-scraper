"""
Scraper específico para IGTP (https://igtp.jobs.personio.com/)
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin
import sys
import os

# Añadir el directorio padre al path para importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IgtpScraper:
    """Scraper específico para la página de empleo de IGTP (Personio)."""
    
    def __init__(self):
        self.base_url = "https://igtp.jobs.personio.com"
        self.empleo_url = "https://igtp.jobs.personio.com/"
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Configura la sesión de requests."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(headers)
    
    def get_page_content(self) -> Optional[BeautifulSoup]:
        """Obtiene el contenido de la página de empleo."""
        try:
            response = self.session.get(self.empleo_url, timeout=30)
            response.raise_for_status()
            
            # Detectar codificación
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.exceptions.RequestException as e:
            return None
    
    def scrape(self) -> List[Dict]:
        """
        Extrae las ofertas de empleo de IGTP.
        
        Returns:
            Lista de diccionarios con la información de las ofertas
        """
        ofertas = []
        soup = self.get_page_content()
        
        if not soup:
            return ofertas
        
        
        # Personio suele usar selectores específicos para ofertas de trabajo
        selectors_to_try = [
            # Selectores típicos de Personio
            'a.job-list-item',
            '.job-item',
            '.position-item',
            '.job-listing-item',
            '.job-card',
            '.position-card',
            
            # Selectores genéricos
            'a[href*="/jobs/"]',
            'a[href*="/job/"]',
            'a[href*="/position/"]',
            
            # Buscar en listas de trabajos
            'ul li a',
            'ol li a',
            
            # Buscar en divs con clases relacionadas
            'div[class*="job"]',
            'div[class*="position"]',
            'div[class*="vacancy"]'
        ]
        
        elements_found = []
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if elements:
                # Filtrar elementos que realmente contengan información de empleo
                filtered_elements = [elem for elem in elements if self._is_employment_related(elem)]
                if filtered_elements:
                    elements_found.extend(filtered_elements)
                    break
        
        # Si no se encontraron elementos específicos, buscar por contenido
        if not elements_found:
            elements_found = self._find_elements_by_content(soup)
        
        # Procesar elementos encontrados
        for element in elements_found:
            oferta = self._extract_oferta_info(element)
            if oferta:
                ofertas.append(oferta)
        
        # Eliminar duplicados
        ofertas = self._remove_duplicates(ofertas)
        
        return ofertas
    
    def _is_employment_related(self, element) -> bool:
        """
        Verifica si un elemento HTML está relacionado con empleo.
        
        Args:
            element: Elemento BeautifulSoup
            
        Returns:
            True si el elemento está relacionado con empleo
        """
        text = element.get_text().lower()
        href = element.get('href', '').lower()
        
        # Palabras clave positivas (deben estar presentes)
        positive_keywords = [
            'empleo', 'trabajo', 'convocatoria', 'oferta', 'vacante',
            'investigador', 'técnico', 'doctor', 'postdoc', 'contrato',
            'plaza', 'puesto', 'candidato', 'solicitud', 'plazo',
            'job', 'position', 'career', 'hiring'
        ]
        
        # Palabras clave negativas (no deben estar presentes)
        negative_keywords = [
            'navegación', 'menú', 'buscar', 'buscador', 'portal',
            'transparencia', 'intranet', 'webmail', 'contacto',
            'quienes somos', 'organización', 'estatutos', 'plan estratégico',
            'navigation', 'menu', 'search', 'footer', 'header'
        ]
        
        # Verificar palabras positivas en texto o href
        has_positive = any(keyword in text or keyword in href for keyword in positive_keywords)
        
        # Verificar palabras negativas
        has_negative = any(keyword in text for keyword in negative_keywords)
        
        # El elemento debe tener palabras positivas y no tener negativas
        return has_positive and not has_negative and len(text.strip()) > 5
    
    def _find_elements_by_content(self, soup: BeautifulSoup) -> List:
        """Busca elementos que contengan texto relacionado con empleo."""
        elements = []
        
        # Buscar en todos los elementos que contengan texto
        all_elements = soup.find_all(['div', 'section', 'article', 'li', 'p', 'a'])
        
        for element in all_elements:
            if self._is_employment_related(element):
                elements.append(element)
        
        return elements[:20]  # Limitar a 20 elementos para evitar ruido
    
    def _extract_oferta_info(self, element) -> Optional[Dict]:
        """
        Extrae información de una oferta desde un elemento HTML.
        
        Args:
            element: Elemento BeautifulSoup
            
        Returns:
            Diccionario con la información de la oferta o None
        """
        oferta = {
            'iis': 'IGTP',
            'titulo': '',
            'fecha_limite': '',
            'enlace': '',
            'descripcion': '',
            'tipo_contrato': '',
            'ubicacion': ''
        }
        
        # Extraer título
        title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.titulo', '.job-title', '.position-title']
        for selector in title_selectors:
            title_elem = element.find(selector)
            if title_elem and title_elem.get_text(strip=True):
                oferta['titulo'] = title_elem.get_text(strip=True)
                break
        
        # Si no se encontró título específico, usar el texto del elemento
        if not oferta['titulo']:
            text = element.get_text(strip=True)
            # Tomar las primeras palabras como título
            words = text.split()[:10]
            oferta['titulo'] = ' '.join(words)
        
        # Extraer enlace
        if element.name == 'a' and element.get('href'):
            href = element['href']
            if href.startswith('http'):
                oferta['enlace'] = href
            else:
                oferta['enlace'] = urljoin(self.base_url, href)
        else:
            # Buscar enlace en el elemento
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    oferta['enlace'] = href
                else:
                    oferta['enlace'] = urljoin(self.base_url, href)
        
        # Extraer fecha límite del texto
        text = element.get_text()
        dates_found = DateParser.extract_dates_from_text(text)
        if dates_found:
            # Usar la fecha más reciente
            latest_date = max(dates_found, key=lambda x: x[1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(latest_date[1])
        
        # Extraer información adicional
        self._extract_additional_info(element, oferta)
        
        # Filtrar ofertas cerradas
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None
        
        # Filtrar cabeceras y elementos no relevantes
        title_lower = oferta['titulo'].lower()
        if any(word in title_lower for word in ['título', 'title', 'cabecera', 'header', 'navigation', 'menú']):
            return None
        
        return oferta
    
    def _extract_additional_info(self, element, oferta: Dict):
        """Extrae información adicional como tipo de contrato y ubicación."""
        text = element.get_text().lower()
        
        # Buscar tipo de contrato
        contratos = ['contrato', 'temporal', 'indefinido', 'postdoc', 'predoc', 'investigador', 'full-time', 'part-time']
        for contrato in contratos:
            if contrato in text:
                oferta['tipo_contrato'] = contrato
                break
        
        # Buscar ubicación
        ubicaciones = ['barcelona', 'madrid', 'valencia', 'sevilla', 'bilbao', 'granada', 'málaga', 'zaragoza']
        for ubicacion in ubicaciones:
            if ubicacion in text:
                oferta['ubicacion'] = ubicacion.title()
                break
    
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
            print("❌ No se encontraron ofertas abiertas en IGTP")
            return
        
        print(f"\n📋 OFERTAS DE EMPLEO - IGTP")
        print(f"{'─' * 50}")
        
        for i, oferta in enumerate(ofertas, 1):
            print(f"{i}. {oferta['titulo']}")
            
            if oferta['fecha_limite']:
                days_left = DateParser.get_days_until_deadline(oferta['fecha_limite'])
                print(f"   📅 Fecha límite: {oferta['fecha_limite']} ({days_left} días restantes)")
            
            if oferta['enlace']:
                print(f"   🔗 Enlace: {oferta['enlace']}")
            
            if oferta['tipo_contrato']:
                print(f"   📝 Tipo: {oferta['tipo_contrato']}")
            
            if oferta['ubicacion']:
                print(f"   📍 Ubicación: {oferta['ubicacion']}")
            
            print()


if __name__ == "__main__":
    scraper = IgtpScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
