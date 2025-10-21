"""
Script principal simplificado para ejecutar todos los scrapers de IIS
Evita problemas de contextos async/sync mezclados
"""

import sys
import os
import json
import time
from typing import Dict, List
from datetime import datetime

# Añadir el directorio padre al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar todos los scrapers
from scrapers.ciberisciii import CiberisciiiPlaywrightScraper
from scrapers.fimabis import FimabisScraper
from scrapers.igtp import IgtpScraper
from scrapers.imib import ImibScraper
from scrapers.idival import IdivalScraper
from scrapers.ibis_sevilla import IbisSevillaScraper
from scrapers.ibs_granada import IbsGranadaScraper
from scrapers.ibsal import IbsalScraper
from scrapers.puerta_hierro import PuertaHierroScraper
from scrapers.idibaps import IdibapsScraper
from scrapers.idis_santiago import IdisSantiagoScraper
from scrapers.iis_la_fe import IisLaFeScraper
from scrapers.iis_princesa import IisPrincesaScraper
from scrapers.iisgm import IisgmScraper
from scrapers.biobizkaia import BiobizkaiaScraper


class IISScraperRunner:
    """Ejecutor simplificado que corre cada scraper individualmente."""
    
    def __init__(self):
        self.scrapers = {
            'CIBERISCIII': CiberisciiiPlaywrightScraper(),
            'FIMABIS': FimabisScraper(),
            'IGTP': IgtpScraper(),
            'IMIB': ImibScraper(),
            'IDIVAL': IdivalScraper(),
            'IBIS_Sevilla': IbisSevillaScraper(),
            'IBS_Granada': IbsGranadaScraper(),
            'IBSAL': IbsalScraper(),
            'Puerta_Hierro': PuertaHierroScraper(),
            'IDIBAPS': IdibapsScraper(),
            'IDIS_Santiago': IdisSantiagoScraper(),
            'IIS_La_Fe': IisLaFeScraper(),
            'IIS_Princesa': IisPrincesaScraper(),
            'IISGM': IisgmScraper(),
            'Biobizkaia': BiobizkaiaScraper()
        }
        
        self.results = {}
    
    def run_all_scrapers(self) -> Dict[str, List[Dict]]:
        """Ejecuta todos los scrapers uno por uno."""
        print("Iniciando scraping simplificado de IIS...")
        print(f"Procesando {len(self.scrapers)} centros...")
        
        for nombre, scraper in self.scrapers.items():
            print(f"\n{'='*50}")
            print(f"Procesando {nombre}")
            print(f"{'='*50}")
            
            try:
                # Ejecutar scraper individualmente
                if nombre == 'CIBERISCIII':
                    # CIBERISCIII necesita contexto async especial
                    import asyncio
                    ofertas = asyncio.run(scraper.scrape_ofertas())
                else:
                    # Todos los demás usan método síncrono
                    ofertas = scraper.scrape()
                
                self.results[nombre] = ofertas
                
                # Mostrar resultados inmediatamente
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
                
                # Delay entre scrapers
                time.sleep(2)
                
            except Exception as e:
                print(f"Error procesando {nombre}: {e}")
                self.results[nombre] = []
        
        return self.results
    
    def save_results(self, filename: str = None):
        """Guarda los resultados en un archivo JSON."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/ofertas_{timestamp}.json"
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Preparar datos para guardar
        data_to_save = {
            'timestamp': datetime.now().isoformat(),
            'total_ofertas': sum(len(ofertas) for ofertas in self.results.values()),
            'centros': {}
        }
        
        for nombre, ofertas in self.results.items():
            data_to_save['centros'][nombre] = {
                'total_ofertas': len(ofertas),
                'ofertas': ofertas
            }
        
        # Guardar archivo
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"\nResultados guardados en: {filename}")
        return filename


def main():
    """Función principal."""
    print("=== SCRAPER IIS SIMPLIFICADO ===")
    print("Ejecutando cada scraper individualmente...")
    print("="*60)
    
    # Crear ejecutor
    runner = IISScraperRunner()
    
    # Ejecutar todos los scrapers
    results = runner.run_all_scrapers()
    
    # Mostrar resumen
    total_ofertas = sum(len(ofertas) for ofertas in results.values())
    print(f"\nTOTAL: {total_ofertas} ofertas")
    print("="*60)
    
    # Mostrar resumen por centro
    print("\nRESUMEN POR CENTRO:")
    print("-" * 30)
    for nombre, ofertas in results.items():
        print(f"{nombre}: {len(ofertas)} ofertas")
    
    # Guardar resultados
    runner.save_results()
    
    print("\nScraping completado!")


if __name__ == "__main__":
    main()