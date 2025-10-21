"""
Main de prueba para los 3 nuevos centros: Puerta_Hierro, IDIBAPS, IDIS_Santiago
"""

import sys
import os
import time
from typing import Dict, List

# Añadir el directorio padre al path para importar scrapers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar scrapers específicos
from scrapers.puerta_hierro import PuertaHierroScraper
from scrapers.idibaps import IdibapsScraper
from scrapers.idis_santiago import IdisSantiagoScraper


class TestScraper:
    """Scraper de prueba para los 3 nuevos centros."""
    
    def __init__(self):
        self.scrapers = {
            'Puerta_Hierro': PuertaHierroScraper(),
            'IDIBAPS': IdibapsScraper(),
            'IDIS_Santiago': IdisSantiagoScraper()
        }
    
    def run_test(self) -> Dict[str, List[Dict]]:
        """Ejecuta el scraping de prueba para los 3 centros."""
        print("Iniciando prueba de scraping para 3 nuevos centros...")
        print("Procesando 3 centros...")
        
        results = {}
        
        for nombre, scraper in self.scrapers.items():
            print(f"\n{'='*50}")
            print(f"Procesando {nombre}")
            print(f"{'='*50}")
            
            try:
                # Ejecutar scraper
                ofertas = scraper.scrape()
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
                time.sleep(2)
                
            except Exception as e:
                print(f"Error procesando {nombre}: {e}")
                results[nombre] = []
        
        return results


def main():
    """Función principal del script de prueba."""
    print("=== PRUEBA DE SCRAPERS PARA 3 NUEVOS CENTROS ===")
    print("Centros: Puerta_Hierro, IDIBAPS, IDIS_Santiago")
    print("="*60)
    
    # Crear instancia del scraper de prueba
    test_scraper = TestScraper()
    
    # Ejecutar prueba
    results = test_scraper.run_test()
    
    # Mostrar total
    total_ofertas = sum(len(ofertas) for ofertas in results.values())
    print(f"\nTOTAL: {total_ofertas} ofertas")
    print("="*60)
    
    print("\nPrueba completada!")
    
    # Mostrar resumen por centro
    print("\nRESUMEN POR CENTRO:")
    print("-" * 30)
    for nombre, ofertas in results.items():
        print(f"{nombre}: {len(ofertas)} ofertas")


if __name__ == "__main__":
    main()
