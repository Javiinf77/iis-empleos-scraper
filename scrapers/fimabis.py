"""
Scraper específico para FIMABIS (https://www.rfgi.es/ConvocatoriasPropiasFIMABIS/es/Convocatorias/DetalleTipoConvocatoria/FIMAB_EM)
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


class FimabisScraper:
    """Scraper específico para la página de empleo de FIMABIS."""
    
    def __init__(self):
        self.base_url = "https://www.rfgi.es"
        self.empleo_url = "https://www.rfgi.es/ConvocatoriasPropiasFIMABIS/es/Convocatorias/DetalleTipoConvocatoria/FIMAB_EM?Estado=A"
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
        Extrae las ofertas de empleo de FIMABIS.
        
        Returns:
            Lista de diccionarios con la información de las ofertas
        """
        ofertas = []
        soup = self.get_page_content()
        
        if not soup:
            return ofertas
        
        
        # FIMABIS usa un sistema tipo Fundanet con tablas de convocatorias
        # Buscar tablas que contengan convocatorias
        tables = soup.find_all('table')
        
        if tables:
            for i, table in enumerate(tables):
                table_ofertas = self._scrape_table_ofertas(table)
                ofertas.extend(table_ofertas)
        
        # Si no hay tablas, buscar listas o divs con convocatorias
        if not ofertas:
            ofertas = self._scrape_list_ofertas(soup)
        
        # Eliminar duplicados
        ofertas = self._remove_duplicates(ofertas)
        
        return ofertas
    
    def _scrape_table_ofertas(self, table) -> List[Dict]:
        """
        Extrae ofertas de una tabla HTML.
        
        Args:
            table: Elemento BeautifulSoup de la tabla
            
        Returns:
            Lista de ofertas encontradas
        """
        ofertas = []
        rows = table.find_all('tr')
        
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            
            if len(cells) >= 2:  # Al menos título y fecha
                oferta = self._extract_oferta_from_row(cells, i)
                if oferta:
                    ofertas.append(oferta)
        
        return ofertas
    
    def _scrape_list_ofertas(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extrae ofertas de listas o divs cuando no hay tablas.
        
        Args:
            soup: BeautifulSoup del contenido completo
            
        Returns:
            Lista de ofertas encontradas
        """
        ofertas = []
        
        # Buscar listas
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists:
            items = list_elem.find_all('li')
            for item in items:
                oferta = self._extract_oferta_info(item)
                if oferta:
                    ofertas.append(oferta)
        
        # Buscar divs con clases relacionadas con convocatorias
        convocatoria_divs = soup.find_all('div', class_=lambda x: x and any(
            word in x.lower() for word in ['convocatoria', 'oferta', 'empleo', 'plaza']
        ))
        
        for div in convocatoria_divs:
            oferta = self._extract_oferta_info(div)
            if oferta:
                ofertas.append(oferta)
        
        return ofertas
    
    def _extract_oferta_from_row(self, cells, row_index: int) -> Optional[Dict]:
        """
        Extrae información de oferta desde una fila de tabla.
        
        Args:
            cells: Lista de celdas de la fila
            row_index: Índice de la fila
            
        Returns:
            Diccionario con la información de la oferta o None
        """
        oferta = {
            'iis': 'FIMABIS',
            'titulo': '',
            'fecha_limite': '',
            'fecha_inicio': '',
            'enlace': '',
            'descripcion': '',
            'estado': 'Abierta',  # Si estamos en la URL con Estado=A, todas están abiertas
            'tipo': 'Empleo'
        }
        
        # Extraer título (primera celda)
        if cells:
            title_cell = cells[0]
            oferta['titulo'] = title_cell.get_text(strip=True)
            
            # Buscar enlaces en la primera celda
            link = title_cell.find('a', href=True)
            if link:
                href = link['href']
                if href.startswith('http'):
                    oferta['enlace'] = href
                else:
                    oferta['enlace'] = urljoin(self.base_url, href)
        
        # La estructura de la tabla es: Título | F.Inicio | F.Fin
        if len(cells) >= 3:
            # Fecha de inicio (segunda celda)
            fecha_inicio_text = cells[1].get_text(strip=True)
            fecha_inicio = DateParser.parse_date(fecha_inicio_text)
            if fecha_inicio:
                oferta['fecha_inicio'] = DateParser.format_date_for_display(fecha_inicio)
            
            # Fecha límite (tercera celda)
            fecha_fin_text = cells[2].get_text(strip=True)
            fecha_fin = DateParser.parse_date(fecha_fin_text)
            if fecha_fin:
                oferta['fecha_limite'] = DateParser.format_date_for_display(fecha_fin)
        
        # Filtrar ofertas con fechas límite pasadas
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None
        
        # Filtrar cabeceras de tabla y elementos no relevantes
        title_lower = oferta['titulo'].lower()
        if any(word in title_lower for word in ['título', 'title', 'cabecera', 'header', 'f.inicio', 'f.fin']):
            return None
        
        return oferta
    
    def _extract_oferta_info(self, element) -> Optional[Dict]:
        """
        Extrae información de una oferta desde un elemento HTML.
        
        Args:
            element: Elemento BeautifulSoup
            
        Returns:
            Diccionario con la información de la oferta o None
        """
        oferta = {
            'iis': 'FIMABIS',
            'titulo': '',
            'fecha_limite': '',
            'enlace': '',
            'descripcion': '',
            'estado': '',
            'tipo': ''
        }
        
        # Extraer título
        title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.titulo', 'a']
        for selector in title_selectors:
            title_elem = element.find(selector)
            if title_elem and title_elem.get_text(strip=True):
                oferta['titulo'] = title_elem.get_text(strip=True)
                break
        
        # Si no se encontró título específico, usar el texto del elemento
        if not oferta['titulo']:
            text = element.get_text(strip=True)
            if len(text) > 100:
                oferta['titulo'] = text[:100] + '...'
            else:
                oferta['titulo'] = text
        
        # Extraer enlace
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
            latest_date = max(dates_found, key=lambda x: x[1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(latest_date[1])
        
        # Extraer estado
        text_lower = text.lower()
        if any(word in text_lower for word in ['abierta', 'abierto', 'activa', 'activo']):
            oferta['estado'] = 'Abierta'
        elif any(word in text_lower for word in ['cerrada', 'cerrado', 'finalizada', 'finalizado']):
            oferta['estado'] = 'Cerrada'
        
        # Filtrar ofertas cerradas
        if oferta['estado'] == 'Cerrada':
            return None
        
        # Filtrar ofertas con fechas límite pasadas
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None
        
        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None
        
        # Filtrar cabeceras de tabla y elementos no relevantes
        title_lower = oferta['titulo'].lower()
        if any(word in title_lower for word in ['título', 'title', 'cabecera', 'header']):
            return None
        
        return oferta
    
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
            print("❌ No se encontraron ofertas abiertas en FIMABIS")
            return
        
        print(f"\n📋 OFERTAS DE EMPLEO - FIMABIS")
        print(f"{'─' * 50}")
        
        for i, oferta in enumerate(ofertas, 1):
            print(f"{i}. {oferta['titulo']}")
            
            if oferta['fecha_inicio']:
                print(f"   📅 Fecha inicio: {oferta['fecha_inicio']}")
            
            if oferta['fecha_limite']:
                days_left = DateParser.get_days_until_deadline(oferta['fecha_limite'])
                print(f"   📅 Fecha límite: {oferta['fecha_limite']} ({days_left} días restantes)")
            
            if oferta['enlace']:
                print(f"   🔗 Enlace: {oferta['enlace']}")
            
            if oferta['estado']:
                print(f"   📊 Estado: {oferta['estado']}")
            
            if oferta['tipo']:
                print(f"   📝 Tipo: {oferta['tipo']}")
            
            print()


if __name__ == "__main__":
    scraper = FimabisScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
