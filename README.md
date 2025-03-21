# LPS MCP - Servidor de Herramientas para Claude

## Descripción General

LPS MCP es un servidor con funciones mínimas para proporcionar herramientas avanzadas para Claude, permitiendo acceso seguro al sistema de archivos y capacidades de pensamiento secuencial. Este servidor forma parte de la infraestructura de LPS para mejorar las capacidades de los asistentes de IA en entornos de trabajo.


## Características

- **Acceso Seguro al Sistema de Archivos**: Navegación y funciones de solo lectura de archivos con límites de seguridad
- **Herramienta de Pensamiento Secuencial**: Capacidad para desglosar problemas complejos en pasos de pensamiento estructurados
- **Configuración Personalizable**: Control sobre qué directorios son accesibles

## Requisitos Previos

- Python 3.10 o superior
- UV (administrador de paquetes Python) instalado y en el PATH del sistema
- Claude Desktop (versión más reciente)

## Instalación

1. **Instalar UV** (si aún no está instalado):

   ```bash
   # Para Windows (PowerShell):
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Para macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Verificar que UV esté en el PATH**:

   ```bash
   uv --version
   ```

3. **Clonar o descargar** este repositorio:

   ```bash
   git clone https://github.com/lpsDevelopers/LPS-MCP
   cd mcp-lps
   ```

4. **Instalar dependencias**:

   ```bash
   uv pip install "mcp[cli]"
   ```

## Configuración con Claude Desktop

1. Abra las configuraciones de Claude Desktop (menú Claude → Configuración → Desarrollador → Editar Configuración)

2. Añada la siguiente configuración a su archivo `claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "lps-mcp": {
         "command": "uv",
         "args": [
           "--directory",
           "path/to/LPS-MCP",
           "run",
           "server.py",
           "path/to/directory"
         ]
       }
     }
   }
   ```

   **Importante**: Reemplace `path/to/LPS-MCP` con la ruta absoluta al directorio donde está guardado `server.py`. El último parámetro es el directorio al que se permitirá acceso (puede añadir múltiples directorios separándolos con comas).

   **Idiomas**: Para usar las herramientas con descripciones en español, seleccione *server_es.py*

3. **Reinicie Claude Desktop** para cargar la nueva configuración.

## Herramientas Disponibles

### Herramientas de Sistema de Archivos

- `read_file`: Lee el contenido de un archivo
- `read_multiple_files`: Lee varios archivos simultáneamente
- `list_directory`: Muestra archivos y directorios en una ubicación
- `directory_tree`: Muestra la estructura de directorios en formato JSON
- `search_files_tool`: Busca archivos por nombre
- `get_file_info`: Muestra metadatos de archivos
- `list_allowed_directories`: Lista los directorios permitidos

### Herramienta de Pensamiento Secuencial

- `sequentialthinking`: Permite a Claude desglosar problemas complejos en pasos de pensamiento estructurados, con capacidad para:
  - Seguir una secuencia lógica de pensamientos
  - Revisar pensamientos anteriores
  - Crear ramificaciones para explorar diferentes enfoques
  - Ajustar dinámicamente el número de pasos necesarios

## Uso

Una vez configurado, puede pedirle a Claude que:

1. **Lea archivos** de las ubicaciones permitidas:
   - "¿Puedes leer el archivo [ruta]?"
   - "Muéstrame el contenido de [ruta]"

2. **Explore directorios**:
   - "¿Qué archivos hay en [directorio]?"
   - "Muéstrame la estructura de archivos en [directorio]"

3. **Utilice pensamiento secuencial**:
   - "Analiza paso a paso el siguiente problema: [problema]"
   - "Desarrolla un plan para [tarea] usando pensamiento secuencial"

4. **Combinar herramientas**:
    - Una vez que Claude haya tomado conocimiento sobre la estructura de un proyecto leyendo la información, puede pedirle que use el pensamiento secuencial para intentar deducir una solución a un problema complejo relacionado con el código.

## Seguridad

Este servidor implementa estrictas medidas de seguridad:

- Acceso restringido solo a los directorios explícitamente permitidos
- Resolución de enlaces simbólicos para prevenir bypass de seguridad
- Validación de todas las rutas solicitadas
- Modo de solo lectura para evitar modificaciones no autorizadas

## Solución de Problemas

- **El servidor no aparece en Claude**: Asegúrese de que UV esté correctamente instalado y en el PATH, y que las rutas en el archivo de configuración sean correctas.
- **Error de acceso denegado**: Verifique que esté intentando acceder a directorios dentro de las rutas permitidas.
- **Claude no encuentra las herramientas**: Reinicie Claude Desktop después de modificar la configuración.

---

LPS
