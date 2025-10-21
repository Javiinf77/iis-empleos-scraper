"""
Utilidades para el parsing y validación de fechas en las convocatorias de empleo.
"""

import re
from datetime import datetime, date
from typing import Optional, List, Tuple


class DateParser:
    """Clase para parsear fechas en diferentes formatos y validar si están abiertas."""
    
    # Patrones de fecha comunes en español
    DATE_PATTERNS = [
        # DD/MM/YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        # DD-MM-YYYY
        r'(\d{1,2})-(\d{1,2})-(\d{4})',
        # DD de MMMM de YYYY
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        # DD MMMM YYYY
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',
        # YYYY-MM-DD
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
    ]
    
    # Mapeo de meses en español
    MONTHS_ES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }
    
    @classmethod
    def parse_date(cls, date_text: str) -> Optional[date]:
        """
        Parsea una fecha desde texto en español.
        
        Args:
            date_text: Texto que contiene la fecha
            
        Returns:
            Objeto date si se puede parsear, None en caso contrario
        """
        if not date_text:
            return None
            
        date_text = date_text.strip().lower()
        
        # Intentar con cada patrón
        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    if pattern == r'(\d{1,2})/(\d{1,2})/(\d{4})':
                        day, month, year = match.groups()
                        return date(int(year), int(month), int(day))
                    
                    elif pattern == r'(\d{1,2})-(\d{1,2})-(\d{4})':
                        day, month, year = match.groups()
                        return date(int(year), int(month), int(day))
                    
                    elif pattern == r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})':
                        day, month_name, year = match.groups()
                        month = cls.MONTHS_ES.get(month_name.lower())
                        if month:
                            return date(int(year), month, int(day))
                    
                    elif pattern == r'(\d{1,2})\s+(\w+)\s+(\d{4})':
                        day, month_name, year = match.groups()
                        month = cls.MONTHS_ES.get(month_name.lower())
                        if month:
                            return date(int(year), month, int(day))
                    
                    elif pattern == r'(\d{4})-(\d{1,2})-(\d{1,2})':
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
                        
                except ValueError:
                    continue
        
        return None
    
    @classmethod
    def is_date_open(cls, date_text: str) -> bool:
        """
        Verifica si una fecha límite está abierta (no ha pasado).
        
        Args:
            date_text: Texto que contiene la fecha límite
            
        Returns:
            True si la fecha está abierta, False si está cerrada
        """
        parsed_date = cls.parse_date(date_text)
        if parsed_date is None:
            return False
        
        today = date.today()
        return parsed_date >= today
    
    @classmethod
    def extract_dates_from_text(cls, text: str) -> List[Tuple[str, date]]:
        """
        Extrae todas las fechas encontradas en un texto.
        
        Args:
            text: Texto donde buscar fechas
            
        Returns:
            Lista de tuplas (texto_original, fecha_parseada)
        """
        dates_found = []
        
        for pattern in cls.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_text = match.group(0)
                parsed_date = cls.parse_date(date_text)
                if parsed_date:
                    dates_found.append((date_text, parsed_date))
        
        return dates_found
    
    @classmethod
    def format_date_for_display(cls, date_obj: date) -> str:
        """
        Formatea una fecha para mostrar al usuario.
        
        Args:
            date_obj: Objeto date a formatear
            
        Returns:
            Fecha formateada como string
        """
        return date_obj.strftime("%d/%m/%Y")
    
    @classmethod
    def get_days_until_deadline(cls, date_text: str) -> Optional[int]:
        """
        Calcula los días restantes hasta la fecha límite.
        
        Args:
            date_text: Texto que contiene la fecha límite
            
        Returns:
            Número de días restantes, None si no se puede parsear
        """
        parsed_date = cls.parse_date(date_text)
        if parsed_date is None:
            return None
        
        today = date.today()
        delta = parsed_date - today
        return delta.days


def test_date_parser():
    """Función de prueba para el parser de fechas."""
    test_cases = [
        "15/12/2024",
        "31-12-2024", 
        "15 de diciembre de 2024",
        "15 diciembre 2024",
        "2024-12-15",
        "Plazo: hasta el 20/01/2025",
        "Fecha límite: 30 de noviembre de 2024"
    ]
    
    print("=== Pruebas del DateParser ===")
    for test in test_cases:
        parsed = DateParser.parse_date(test)
        is_open = DateParser.is_date_open(test)
        days_left = DateParser.get_days_until_deadline(test)
        
        print(f"Texto: '{test}'")
        print(f"  Parseado: {parsed}")
        print(f"  Abierto: {is_open}")
        print(f"  Días restantes: {days_left}")
        print()


if __name__ == "__main__":
    test_date_parser()
