"""
Scraper específico para IISGM
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import sys
import os
import re

# Añadir el directorio padre al path para importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IisgmScraper:
    """Scraper específico para IISGM."""
    
    def __init__(self):
        self.empleo_url = "https://www.iisgm.com/ofertas-de-empleo/"
        self.date_parser = DateParser()
    
    def scrape(self) -> List[Dict]:
        """
        Extrae las ofertas de empleo de IISGM.
        
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
            
            # Buscar divs que contengan tanto enlaces como status
            divs_con_ofertas = soup.find_all('div')
            
            for div in divs_con_ofertas:
                enlaces = div.find_all('a', href=True)
                status_elements = div.find_all('p', class_=re.compile(r'status'))
                
                # Solo procesar divs que tengan tanto enlaces como status
                if enlaces and status_elements:
                    for link in enlaces:
                        # Verificar si este enlace está asociado con un status "Abierta"
                        if self._is_oferta_abierta_en_div(link, div):
                            oferta = self._extract_oferta_info(link)
                            if oferta and self._is_valid_oferta(oferta):
                                ofertas.append(oferta)
            
        except Exception as e:
            print(f"Error scraping IISGM: {e}")
        
        # Deduplicar ofertas por enlace
        ofertas_unicas = []
        enlaces_vistos = set()
        
        for oferta in ofertas:
            if oferta['enlace'] not in enlaces_vistos:
                ofertas_unicas.append(oferta)
                enlaces_vistos.add(oferta['enlace'])
        
        return ofertas_unicas
    
    def _is_oferta_abierta_en_div(self, link_element, div_element) -> bool:
        """Verifica si una oferta está abierta basándose en el div contenedor."""
        # Buscar el elemento p que tenga tanto la clase 'status' como 'status--0'
        status_elements = div_element.find_all('p', class_='status')
        
        # Contar cuántos elementos de cada tipo hay
        abiertas = 0
        cerradas = 0
        
        for status_elem in status_elements:
            classes = status_elem.get('class', [])
            texto = status_elem.get_text(strip=True).lower()
            
            if 'status--0' in classes and 'abierta' in texto:
                abiertas += 1
            elif 'status--1' in classes and 'cerrada' in texto:
                cerradas += 1
        
        # Solo considerar abierta si hay más elementos abiertos que cerrados
        # o si solo hay elementos abiertos
        return abiertas > cerradas
    
    def _is_oferta_abierta(self, link_element) -> bool:
        """Verifica si una oferta está abierta basándose en el contexto del elemento."""
        # Buscar específicamente el p con clase "status status--0" que contiene "Abierta"
        status_p = link_element.find('p', class_='status status--0')
        if status_p and 'abierta' in status_p.get_text().lower():
            return True
        
        # Buscar en el elemento padre
        parent = link_element.parent
        if parent:
            status_p = parent.find('p', class_='status status--0')
            if status_p and 'abierta' in status_p.get_text().lower():
                return True
        
        # Buscar en elementos hermanos
        siblings = link_element.find_next_siblings()
        for sibling in siblings:
            status_p = sibling.find('p', class_='status status--0')
            if status_p and 'abierta' in status_p.get_text().lower():
                return True
        
        # Buscar en elementos anteriores
        previous_siblings = link_element.find_previous_siblings()
        for sibling in previous_siblings:
            status_p = sibling.find('p', class_='status status--0')
            if status_p and 'abierta' in status_p.get_text().lower():
                return True
        
        # Buscar en elementos hermanos más amplios (divs contenedores)
        current = link_element
        for _ in range(3):  # Buscar hasta 3 niveles hacia arriba
            if current.parent:
                current = current.parent
                status_p = current.find('p', class_='status status--0')
                if status_p and 'abierta' in status_p.get_text().lower():
                    return True
        
        return False
    
    def _extract_oferta_info(self, element) -> Dict:
        """Extrae información de una oferta desde un elemento HTML."""
        oferta = {
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'enlace': '',
            'centro': 'IISGM',
            'descripcion': ''
        }
        
        # El elemento ya es un enlace, extraer información directamente
        if element.name == 'a' and 'href' in element.attrs:
            href = element['href']
            if href.startswith('http'):
                oferta['enlace'] = href
            else:
                oferta['enlace'] = f"https://www.iisgm.com{href}"
            
            # Extraer título del texto del enlace
            titulo = element.get_text(strip=True)
            if titulo and len(titulo) > 5:
                oferta['titulo'] = titulo
        
        # Si no se encontró título, usar el texto del elemento
        if not oferta['titulo']:
            text = element.get_text(strip=True)
            if text and len(text) > 10:
                oferta['titulo'] = text[:100] + '...' if len(text) > 100 else text
        
        return oferta
    
    def _is_valid_oferta(self, oferta: Dict) -> bool:
        """Valida si una oferta es válida y está abierta."""
        # Debe tener título y enlace
        if not oferta['titulo'] or len(oferta['titulo']) < 5:
            return False
        
        if not oferta['enlace'] or not oferta['enlace'].startswith('http'):
            return False
        
        # Debe ser un enlace a una oferta específica
        if '/ofertas-de-empleo/' not in oferta['enlace']:
            return False
        
        return True


if __name__ == '__main__':
    scraper = IisgmScraper()
    ofertas = scraper.scrape()
    print(f"Encontradas {len(ofertas)} ofertas")
