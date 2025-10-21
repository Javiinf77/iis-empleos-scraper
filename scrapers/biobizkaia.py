import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from utils.date_parser import DateParser

class BiobizkaiaScraper:
    def __init__(self):
        self.base_url = "https://gestiononline.bioef.eus"
        self.empleo_url = "https://gestiononline.bioef.eus/ConvocatoriasPropiasBiobizkaia/es/Convocatorias/DetalleTipoConvocatoria/OFBIO"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape(self):
        """Scrape job offers from Biobizkaia"""
        try:
            response = self.session.get(self.empleo_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            ofertas = []
            
            # Buscar tabla de convocatorias (similar a FIMABIS)
            tabla = soup.find('table')
            if tabla:
                filas = tabla.find_all('tr')
                for fila in filas[1:]:  # Saltar encabezado
                    oferta = self._extract_oferta_from_row(fila)
                    if oferta and self._is_valid_oferta(oferta):
                        ofertas.append(oferta)
            
            # Si no hay tabla, buscar elementos con clase específica
            if not ofertas:
                oferta_elements = soup.find_all(['div', 'article'], class_=re.compile(r'oferta|convocatoria|item', re.I))
                for element in oferta_elements:
                    oferta = self._extract_oferta_info(element)
                    if oferta and self._is_valid_oferta(oferta):
                        ofertas.append(oferta)
            
            return ofertas
            
        except requests.RequestException as e:
            print(f"Error al acceder a Biobizkaia: {e}")
            return []
        except Exception as e:
            print(f"Error inesperado en Biobizkaia: {e}")
            return []
    
    def _extract_oferta_from_row(self, fila):
        """Extraer información de una fila de tabla"""
        try:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 3:
                return None
            
            # Estructura típica: Título, Fecha inicio, Fecha límite, Estado, etc.
            titulo = celdas[0].get_text(strip=True) if len(celdas) > 0 else ""
            fecha_inicio = celdas[1].get_text(strip=True) if len(celdas) > 1 else ""
            fecha_limite = celdas[2].get_text(strip=True) if len(celdas) > 2 else ""
            estado = celdas[3].get_text(strip=True) if len(celdas) > 3 else ""
            
            # Buscar enlace
            enlace_elem = fila.find('a', href=True)
            enlace = ""
            if enlace_elem:
                href = enlace_elem['href']
                if href.startswith('/'):
                    enlace = self.base_url + href
                elif href.startswith('http'):
                    enlace = href
            
            return {
                'titulo': titulo,
                'fecha_inicio': fecha_inicio,
                'fecha_limite': fecha_limite,
                'enlace': enlace,
                'estado': estado,
                'provincia': 'Bizkaia',
                'centro': 'Biobizkaia'
            }
            
        except Exception as e:
            return None
    
    def _extract_oferta_info(self, element):
        """Extraer información de una oferta desde elemento genérico"""
        try:
            # Buscar título
            titulo_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'], string=re.compile(r'.+'))
            if not titulo_elem:
                titulo_elem = element.find(['a', 'span', 'div'], class_=re.compile(r'title|titulo', re.I))
            
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else ""
            
            # Buscar enlace
            enlace_elem = element.find('a', href=True)
            enlace = ""
            if enlace_elem:
                href = enlace_elem['href']
                if href.startswith('/'):
                    enlace = self.base_url + href
                elif href.startswith('http'):
                    enlace = href
            
            # Buscar fechas en el texto
            texto_completo = element.get_text()
            fechas = DateParser.extract_dates_from_text(texto_completo)
            
            fecha_inicio = fechas[0] if len(fechas) > 0 else ""
            fecha_limite = fechas[1] if len(fechas) > 1 else ""
            
            # Si no hay fechas específicas, usar fechas por defecto
            if not fecha_limite:
                fecha_limite = "31/12/2025"  # Fecha por defecto para ofertas abiertas
            
            return {
                'titulo': titulo,
                'fecha_inicio': fecha_inicio,
                'fecha_limite': fecha_limite,
                'enlace': enlace,
                'provincia': 'Bizkaia',
                'centro': 'Biobizkaia'
            }
            
        except Exception as e:
            return None
    
    def _is_valid_oferta(self, oferta):
        """Validar si la oferta es válida"""
        if not oferta:
            return False
        
        # Verificar que tenga título
        if not oferta.get('titulo') or len(oferta['titulo']) < 5:
            return False
        
        # Verificar que no sea un elemento genérico
        titulo = oferta['titulo'].lower()
        exclude_keywords = ['menu', 'navegación', 'footer', 'header', 'cookie', 'política', 'aviso legal', 'título']
        
        if any(keyword in titulo for keyword in exclude_keywords):
            return False
        
        # Verificar estado si existe
        if oferta.get('estado'):
            estado = oferta['estado'].lower()
            if 'cerrada' in estado or 'finalizada' in estado:
                return False
        
        # Verificar fecha límite si existe
        if oferta.get('fecha_limite'):
            if not DateParser.is_date_open(oferta['fecha_limite']):
                return False
        
        return True
