"""
Scraper para IDIS Santiago: https://www.idisantiago.es/empleo/
Lista con título, descripción y círculo verde (abierto) o rojo (cerrado)
"""

import sys
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_parser import DateParser


class IdisSantiagoScraper:
    def __init__(self):
        self.base_url = "https://empleo.idisantiago.es"
        self.empleo_url = "https://empleo.idisantiago.es/ofertastrabajo/publicadas"
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
            # Forzar UTF-8 para evitar problemas de codificación
            resp.encoding = 'utf-8'
            return BeautifulSoup(resp.content, 'html.parser')
        except requests.RequestException:
            return None

    def scrape(self) -> List[Dict]:
        soup = self.fetch()
        if not soup:
            return []

        ofertas: List[Dict] = []

        # Buscar elementos que contengan ofertas de trabajo
        # Cada oferta parece estar en un bloque con título de titulación
        offer_blocks = soup.find_all(['div', 'section', 'article'], string=lambda text: text and 'TITULACIÓN REQUERIDA' in text)
        
        # Si no encontramos por texto, buscar por estructura HTML
        if not offer_blocks:
            # Buscar elementos que contengan información de ofertas
            offer_blocks = soup.find_all(['div', 'section', 'article'], class_=lambda x: x and any(
                word in x.lower() for word in ['oferta', 'convocatoria', 'empleo', 'trabajo']
            ))
        
        # Si aún no encontramos, buscar elementos que contengan "Abierto" o "Cerrado"
        if not offer_blocks:
            status_elements = soup.find_all(['div', 'section', 'article'], string=lambda text: text and ('Abierto' in text or 'Cerrado' in text))
            for status_elem in status_elements:
                parent = status_elem.find_parent(['div', 'section', 'article'])
                if parent:
                    offer_blocks.append(parent)

        for block in offer_blocks:
            oferta = self._parse_offer_block(block)
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

    def _parse_offer_block(self, block) -> Optional[Dict]:
        """Extrae información de un bloque de oferta de IDIS Santiago."""
        oferta = {
            'iis': 'IDIS_Santiago',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Santiago de Compostela',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIS Santiago',
            'enlace': '',
            'referencia': ''
        }

        try:
            # Obtener todo el texto del bloque
            text = block.get_text()
            
            # Buscar número de referencia (formato: XXX/2025)
            import re
            ref_match = re.search(r'(\d+/2025)', text)
            if ref_match:
                oferta['referencia'] = ref_match.group(1)
            
            # Buscar fechas (formato: DD/MM/YYYY)
            fecha_pattern = r'(\d{2}/\d{2}/\d{4})'
            fechas = re.findall(fecha_pattern, text)
            if len(fechas) >= 2:
                oferta['fecha_inicio'] = DateParser.format_date_for_display(DateParser.parse_date(fechas[0]))
                oferta['fecha_limite'] = DateParser.format_date_for_display(DateParser.parse_date(fechas[1]))
            
            # Buscar estado
            if 'Abierto' in text:
                oferta['estado'] = 'Abierta'
            elif 'Cerrado' in text:
                oferta['estado'] = 'Cerrada'
            
            # Extraer título del puesto
            # Buscar texto después de "#####" que parece ser el título del puesto
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('#####'):
                    # El título está en la siguiente línea
                    if i + 1 < len(lines):
                        titulo = lines[i + 1].strip()
                        if titulo and len(titulo) > 5:
                            oferta['titulo'] = titulo
                            break
                elif 'TITULADO/A' in line or 'TÉCNICO/A' in line or 'INVESTIGADOR' in line:
                    # Usar esta línea como título si no encontramos otro
                    if not oferta['titulo']:
                        oferta['titulo'] = line
            
            # Si no encontramos título específico, usar la primera línea significativa
            if not oferta['titulo']:
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10 and not line.startswith('#'):
                        oferta['titulo'] = line[:200]  # Limitar longitud
                        break
            
            # Buscar enlace "Inscribirse" o "Más información"
            link_elem = block.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)

        except Exception:
            return None

        # Filtrar ofertas cerradas
        if oferta['estado'] == 'Cerrada':
            return None
        
        # Filtrar por fecha límite
        if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
            return None

        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        return oferta

    def _parse_element(self, element) -> Optional[Dict]:
        oferta = {
            'iis': 'IDIS_Santiago',
            'titulo': '',
            'fecha_inicio': '',
            'fecha_limite': '',
            'estado': '',
            'provincia': 'Santiago de Compostela',
            'categoria': '',
            'titulacion': '',
            'centro': 'IDIS Santiago',
            'enlace': ''
        }

        # Buscar título
        title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.titulo', '.job-title', 'a']
        for selector in title_selectors:
            title_elem = element.find(selector)
            if title_elem and title_elem.get_text(strip=True):
                oferta['titulo'] = title_elem.get_text(strip=True)
                break

        # Si no encontramos título específico, usar el texto del elemento
        if not oferta['titulo']:
            text = element.get_text(strip=True)
            if len(text) > 20 and len(text) < 200:  # Filtrar textos muy cortos o muy largos
                oferta['titulo'] = text

        # Buscar enlace
        link_elem = element.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            oferta['enlace'] = href if href.startswith('http') else urljoin(self.base_url, href)

        # Buscar indicador de estado (círculo verde/rojo)
        # Buscar elementos con clases o estilos que indiquen estado
        status_indicators = element.find_all(['span', 'div', 'i'], class_=lambda x: x and any(
            word in x.lower() for word in ['green', 'red', 'open', 'closed', 'abierto', 'cerrado', 'activo', 'inactivo']
        ))
        
        # También buscar por colores en estilos
        style_elements = element.find_all(attrs={'style': lambda x: x and any(
            color in x.lower() for color in ['green', 'red', '#00ff00', '#ff0000', '#0f0', '#f00']
        )})

        # Determinar estado
        text_lower = element.get_text().lower()
        if any(word in text_lower for word in ['abierto', 'abierta', 'activo', 'activa', 'disponible']):
            oferta['estado'] = 'Abierta'
        elif any(word in text_lower for word in ['cerrado', 'cerrada', 'finalizado', 'finalizada']):
            oferta['estado'] = 'Cerrada'
        elif status_indicators or style_elements:
            # Si hay indicadores visuales, asumir que está abierto
            oferta['estado'] = 'Abierta'
        else:
            # Si no hay indicadores claros, asumir abierto si tiene título válido
            oferta['estado'] = 'Abierta' if oferta['titulo'] else ''

        # Buscar fechas en el texto
        text = element.get_text()
        dates = DateParser.extract_dates_from_text(text)
        if dates:
            dates_sorted = sorted(dates, key=lambda x: x[1])
            oferta['fecha_inicio'] = DateParser.format_date_for_display(dates_sorted[0][1])
            oferta['fecha_limite'] = DateParser.format_date_for_display(dates_sorted[-1][1])
            
            # Filtrar por fecha límite
            if oferta['fecha_limite'] and not DateParser.is_date_open(oferta['fecha_limite']):
                return None

        # Filtrar ofertas cerradas
        if oferta['estado'] == 'Cerrada':
            return None

        # Filtrar elementos sin título válido
        if len(oferta['titulo']) < 5:
            return None

        # Filtrar elementos que parecen ser navegación, menús o redes sociales
        title_lower = oferta['titulo'].lower()
        if any(word in title_lower for word in [
            'inicio', 'contacto', 'aviso', 'política', 'cookies', 'menú', 'navegación',
            'facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'redes sociales',
            'únete al equipo', 'síguenos', 'síguenos en', 'conecta con nosotros'
        ]):
            return None
        
        # Filtrar enlaces a redes sociales o páginas externas
        if oferta['enlace']:
            enlace_lower = oferta['enlace'].lower()
            if any(domain in enlace_lower for domain in [
                'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 
                'youtube.com', 'sanidade.xunta.gal', 'xunta.gal'
            ]):
                return None

        return oferta


def test_idis_santiago():
    print('Probando scraper IDIS Santiago...')
    s = IdisSantiagoScraper()
    ofertas = s.scrape()
    if not ofertas:
        print('Sin ofertas')
        return ofertas
    print('OFERTAS - IDIS Santiago')
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
    test_idis_santiago()
