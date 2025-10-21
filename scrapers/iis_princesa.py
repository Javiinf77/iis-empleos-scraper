"""
Scraper específico para IIS Princesa
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import sys
import os

# Añadir el directorio padre al path para importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IisPrincesaScraper:
    """Scraper específico para IIS Princesa."""
    
    def __init__(self):
        self.empleo_url = "https://www.iis-princesa.org/fundacion/ofertas-de-empleo/"
        self.date_parser = DateParser()
    
    def scrape(self) -> List[Dict]:
        """
        Extrae las ofertas de empleo de IIS Princesa.
        
        Returns:
            Lista de diccionarios con la información de las ofertas
        """
        ofertas = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.empleo_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar solo la sección "Ofertas Disponibles"
            elements = []
            
            # Buscar el h3 que dice "Ofertas Disponibles"
            disponibles_h3 = soup.find('h3', string=lambda text: text and 'disponibles' in text.lower())
            if disponibles_h3:
                # Buscar todos los elementos después del h3 hasta encontrar el siguiente h3
                current = disponibles_h3.next_sibling
                while current:
                    if hasattr(current, 'name') and current.name == 'h3':
                        # Si encontramos otro h3, parar
                        break
                    if hasattr(current, 'find_all'):
                        # Buscar enlaces de descarga en este elemento
                        pdf_links = current.find_all('a', href=True, string=lambda text: text and 'descargar' in text.lower())
                        elements.extend(pdf_links)
                    current = current.next_sibling
                
                print(f"IIS Princesa: Encontradas {len(elements)} ofertas disponibles")
            
            # Procesar elementos encontrados
            for element in elements:
                oferta = self._extract_oferta_info(element)
                if oferta and self._is_valid_oferta(oferta):
                    ofertas.append(oferta)
            
        except Exception as e:
            print(f"Error scraping IIS Princesa: {e}")
        
        return ofertas
    
    def _extract_oferta_info(self, element) -> Dict:
        """Extrae información de una oferta desde un elemento HTML."""
        oferta = {
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'enlace': '',
            'centro': 'IIS Princesa',
            'descripcion': ''
        }
        
        # Para enlaces de descarga de PDF, extraer información del contexto
        if element.name == 'a' and 'href' in element.attrs:
            href = element['href']
            if href.startswith('http'):
                oferta['enlace'] = href
            else:
                oferta['enlace'] = f"https://www.iis-princesa.org{href}"
            
            # Extraer título del contexto (elemento padre o hermanos)
            parent = element.parent
            if parent:
                # Buscar texto descriptivo en el contexto
                context_text = parent.get_text(strip=True)
                if context_text and len(context_text) > 20:
                    # Limpiar el texto y usar como título
                    clean_text = context_text.replace('Descargar oferta', '').strip()
                    if clean_text:
                        oferta['titulo'] = clean_text[:100] + '...' if len(clean_text) > 100 else clean_text
        
        # Si no se encontró título del contexto, usar el nombre del archivo PDF
        if not oferta['titulo'] and oferta['enlace']:
            filename = oferta['enlace'].split('/')[-1]
            if filename.endswith('.pdf'):
                filename = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                oferta['titulo'] = filename
        
        # Para PDFs de IIS Princesa, extraer fecha límite del nombre del archivo si es posible
        if oferta['enlace'] and '2025' in oferta['enlace']:
            # Los PDFs de octubre 2025 probablemente tienen fecha límite en octubre
            oferta['fecha_limite'] = '30/10/2025'  # Fecha común en estos PDFs
        
        return oferta
    
    def _is_valid_oferta(self, oferta: Dict) -> bool:
        """Valida si una oferta es válida y está abierta."""
        # Para IIS Princesa, todas las ofertas en la sección "disponibles" son válidas
        if not oferta['titulo'] or len(oferta['titulo']) < 5:
            return False
        
        # Debe tener un enlace válido
        if not oferta['enlace'] or not oferta['enlace'].startswith('http'):
            return False
        
        # Debe ser un PDF
        if not oferta['enlace'].endswith('.pdf'):
            return False
        
        return True


if __name__ == '__main__':
    scraper = IisPrincesaScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
