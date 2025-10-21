# IIS Empleos Scraper

Web scraper para monitorizar ofertas de empleo de Institutos de Investigación Sanitaria (IIS) de España.

## 🎯 Objetivo

El sistema consulta diariamente las webs oficiales de empleo de cada IIS y detecta nuevas convocatorias abiertas, mostrando su título, fecha límite y enlace.

## 📊 Centros incluidos

### Centros activos (8):
- **CIBERISCIII** - Centro de Investigación Biomédica en Red
- **FIMABIS** - Fundación para la Investigación Biomédica de Andalucía Oriental
- **IGTP** - Instituto de Investigación Germans Trias i Pujol
- **IMIB** - Instituto Murciano de Investigación Biosanitaria
- **IDIVAL** - Instituto de Investigación Sanitaria Valdecilla
- **IBIS Sevilla** - Instituto de Biomedicina de Sevilla
- **IBS Granada** - Instituto de Investigación Biosanitaria de Granada
- **IBSAL** - Instituto de Investigación Biomédica de Salamanca

### Centros en desarrollo (3):
- **Puerta_Hierro** - Hospital Universitario Puerta de Hierro-Majadahonda
- **IDIBAPS** - Institut d'Investigacions Biomèdiques August Pi i Sunyer
- **IDIS Santiago** - Instituto de Investigación Sanitaria de Santiago de Compostela

## 🛠️ Tecnologías

- **Python 3.8+**
- **requests** - Para descargar HTML
- **BeautifulSoup4** - Para parsear contenido
- **Playwright** - Para contenido dinámico (JavaScript)
- **lxml** - Parser XML/HTML rápido

## 📦 Instalación

```bash
# Clonar repositorio
git clone https://github.com/TU_USUARIO/iis-empleos-scraper.git
cd iis-empleos-scraper

# Instalar dependencias
pip install -r iisempleos/requirements.txt

# Instalar Playwright (para contenido dinámico)
playwright install chromium
```

## 🚀 Uso

```bash
# Ejecutar scraper principal
python iisempleos/main.py

# Probar nuevos centros
python iisempleos/maindeprueba.py
```

## 📁 Estructura del proyecto

```
iisempleos/
├── config/
│   └── webs.json              # Configuración de centros IIS
├── scrapers/
│   ├── ciberisciii.py         # Scraper CIBERISCIII
│   ├── fimabis.py             # Scraper FIMABIS
│   ├── igtp.py                # Scraper IGTP
│   ├── imib.py                # Scraper IMIB
│   ├── idival.py              # Scraper IDIVAL
│   ├── ibis_sevilla.py        # Scraper IBIS Sevilla
│   ├── ibs_granada.py         # Scraper IBS Granada
│   ├── ibsal.py               # Scraper IBSAL
│   ├── puerta_hierro.py       # Scraper Puerta de Hierro
│   ├── idibaps.py             # Scraper IDIBAPS
│   └── idis_santiago.py       # Scraper IDIS Santiago
├── utils/
│   └── date_parser.py         # Utilidades para fechas
├── data/
│   └── ofertas_vistas.json    # Registro de ofertas detectadas
├── main.py                    # Script principal
├── maindeprueba.py            # Script de prueba para nuevos centros
└── requirements.txt           # Dependencias Python
```

## 🔧 Configuración

El archivo `config/webs.json` contiene la configuración de cada centro:

```json
{
  "nombre": "CIBERISCIII",
  "url": "https://www.ciberisciii.es/empleo",
  "tipo": "html_dinamico",
  "scraper": "ciberisciii.py",
  "activo": true
}
```

## 📈 Estado del proyecto

- ✅ **8 centros funcionando** correctamente
- 🔄 **3 centros en desarrollo** (Puerta_Hierro, IDIBAPS, IDIS_Santiago)
- 🎯 **Próximo objetivo**: Integrar los 3 nuevos centros al sistema principal

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nuevo-centro`)
3. Commit tus cambios (`git commit -m 'Añadir nuevo centro'`)
4. Push a la rama (`git push origin feature/nuevo-centro`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
