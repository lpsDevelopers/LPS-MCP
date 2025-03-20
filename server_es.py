#!/usr/bin/env python3

import os
import json
import sys
import pathlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, TypedDict

from mcp.server.fastmcp import FastMCP, Context

# Create a FastMCP server instance
mcp = FastMCP("secure-filesystem-server")

# Command line argument parsing
if len(sys.argv) < 2:
    print("Usage: python filesystem_server.py <allowed-directory> [additional-directories...]", file=sys.stderr)
    sys.exit(1)

# Normalize all paths consistently
def normalize_path(p: str) -> str:
    return os.path.normpath(p)

def expand_home(filepath: str) -> str:
    if filepath.startswith('~/') or filepath == '~':
        return os.path.join(os.path.expanduser('~'), filepath[1:])
    return filepath

# Store allowed directories in normalized form
allowed_directories = [
    normalize_path(os.path.abspath(expand_home(dir)))
    for dir in sys.argv[1:]
]

# Validate that all directories exist and are accessible
for dir_path in sys.argv[1:]:
    expanded_path = expand_home(dir_path)
    try:
        stats = os.stat(expanded_path)
        if not os.path.isdir(expanded_path):
            print(f"Error: {dir_path} is not a directory", file=sys.stderr)
            sys.exit(1)
    except OSError as e:
        print(f"Error accessing directory {dir_path}: {e}", file=sys.stderr)
        sys.exit(1)

# Security utilities
async def validate_path(requested_path: str) -> str:
    """Valida y resuelve las rutas de archivos contra directorios permitidos por seguridad."""
    expanded_path = expand_home(requested_path)
    absolute = os.path.abspath(expanded_path)
    normalized_requested = normalize_path(absolute)
    
    # Check if path is within allowed directories
    is_allowed = any(normalized_requested.startswith(dir) for dir in allowed_directories)
    if not is_allowed:
        raise ValueError(f"Acceso denegado - ruta fuera de los directorios permitidos: {absolute} no está en {', '.join(allowed_directories)}")
    
    # Handle symlinks by checking their real path
    try:
        real_path = os.path.realpath(absolute)
        normalized_real = normalize_path(real_path)
        is_real_path_allowed = any(normalized_real.startswith(dir) for dir in allowed_directories)
        if not is_real_path_allowed:
            raise ValueError("Acceso denegado - destino del enlace simbólico fuera de los directorios permitidos")
        return real_path
    except OSError:
        # For paths that don't exist yet, verify parent directory
        parent_dir = os.path.dirname(absolute)
        try:
            real_parent_path = os.path.realpath(parent_dir)
            normalized_parent = normalize_path(real_parent_path)
            is_parent_allowed = any(normalized_parent.startswith(dir) for dir in allowed_directories)
            if not is_parent_allowed:
                raise ValueError("Acceso denegado - directorio padre fuera de los directorios permitidos")
            return absolute
        except OSError:
            raise ValueError(f"El directorio padre no existe: {parent_dir}")

async def get_file_stats(file_path: str) -> Dict[str, Union[int, str, bool]]:
    """Obtiene información detallada del archivo."""
    stats = os.stat(file_path)
    return {
        "size": stats.st_size,
        "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
        "isDirectory": os.path.isdir(file_path),
        "isFile": os.path.isfile(file_path),
        "permissions": oct(stats.st_mode)[-3:],
    }

async def search_files(
    root_path: str,
    pattern: str,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Busca archivos que coincidan con un patrón, con exclusiones opcionales."""
    if exclude_patterns is None:
        exclude_patterns = []
    
    results = []
    
    for root, dirs, files in os.walk(root_path):
        # Check if we should process this directory based on exclude patterns
        try:
            # Validate each path before processing
            await validate_path(root)
            
            # Filter out directories in exclude list
            rel_path = os.path.relpath(root, root_path)
            dirs[:] = [d for d in dirs if not any(
                os.path.relpath(os.path.join(root, d), root_path).startswith(exclude_pattern)
                for exclude_pattern in exclude_patterns
            )]
            
            # Check all entries in this directory
            for name in dirs + files:
                full_path = os.path.join(root, name)
                try:
                    await validate_path(full_path)
                    if pattern.lower() in name.lower():
                        results.append(full_path)
                except ValueError:
                    # Skip invalid paths
                    continue
                    
        except ValueError:
            # Skip invalid paths
            continue
    
    return results

# Sequential Thinking Tool
class ThoughtData(TypedDict, total=False):
    thought: str
    thoughtNumber: int
    totalThoughts: int
    nextThoughtNeeded: bool
    isRevision: Optional[bool]
    revisesThought: Optional[int]
    branchFromThought: Optional[int]
    branchId: Optional[str]
    needsMoreThoughts: Optional[bool]

class SequentialThinkingServer:
    def __init__(self):
        self.thought_history = []
        self.branches = {}
    
    def validate_thought_data(self, data: Dict[str, Any]) -> ThoughtData:
        if not isinstance(data.get('thought'), str):
            raise ValueError('Invalid thought: must be a string')
        if not isinstance(data.get('thoughtNumber'), int):
            raise ValueError('Invalid thoughtNumber: must be a number')
        if not isinstance(data.get('totalThoughts'), int):
            raise ValueError('Invalid totalThoughts: must be a number')
        if not isinstance(data.get('nextThoughtNeeded'), bool):
            raise ValueError('Invalid nextThoughtNeeded: must be a boolean')
        
        return {
            'thought': data['thought'],
            'thoughtNumber': data['thoughtNumber'],
            'totalThoughts': data['totalThoughts'],
            'nextThoughtNeeded': data['nextThoughtNeeded'],
            'isRevision': data.get('isRevision'),
            'revisesThought': data.get('revisesThought'),
            'branchFromThought': data.get('branchFromThought'),
            'branchId': data.get('branchId'),
            'needsMoreThoughts': data.get('needsMoreThoughts')
        }
    
    def format_thought(self, thought_data: ThoughtData) -> str:
        """Formatea un pensamiento con bordes coloreados y contexto"""
        thought_num = thought_data['thoughtNumber']
        total = thought_data['totalThoughts']
        thought = thought_data['thought']
        is_revision = thought_data.get('isRevision', False)
        revises = thought_data.get('revisesThought')
        branch_from = thought_data.get('branchFromThought')
        branch_id = thought_data.get('branchId')
        
        # Create appropriate prefix and context
        if is_revision:
            prefix = "🔄 Revisión"
            context = f" (revisando pensamiento {revises})"
        elif branch_from:
            prefix = "🌿 Rama"
            context = f" (desde pensamiento {branch_from}, ID: {branch_id})"
        else:
            prefix = "💭 Pensamiento"
            context = ""
        
        header = f"{prefix} {thought_num}/{total}{context}"
        border_len = max(len(header), len(thought)) + 4
        border = "─" * border_len
        
        # Build the formatted output
        output = f"\n┌{border}┐\n"
        output += f"│ {header.ljust(border_len)} │\n"
        output += f"├{border}┤\n"
        output += f"│ {thought.ljust(border_len)} │\n"
        output += f"└{border}┘"
        
        return output
    
    def process_thought(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa un pensamiento y devuelve la respuesta"""
        try:
            validated_input = self.validate_thought_data(input_data)
            
            if validated_input['thoughtNumber'] > validated_input['totalThoughts']:
                validated_input['totalThoughts'] = validated_input['thoughtNumber']
            
            self.thought_history.append(validated_input)
            
            # Track branches if applicable
            if validated_input.get('branchFromThought') and validated_input.get('branchId'):
                branch_id = validated_input['branchId']
                if branch_id not in self.branches:
                    self.branches[branch_id] = []
                self.branches[branch_id].append(validated_input)
            
            # Format and log the thought
            formatted_thought = self.format_thought(validated_input)
            print(formatted_thought, file=sys.stderr)
            
            # Return response
            return {
                'thoughtNumber': validated_input['thoughtNumber'],
                'totalThoughts': validated_input['totalThoughts'],
                'nextThoughtNeeded': validated_input['nextThoughtNeeded'],
                'branches': list(self.branches.keys()),
                'thoughtHistoryLength': len(self.thought_history)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }

# Create a single instance of the sequential thinking server
thinking_server = SequentialThinkingServer()

# Tool implementations
@mcp.tool()
async def read_file(path: str) -> str:
    """Lee el contenido completo de un archivo del sistema de archivos.
    
    Maneja varias codificaciones de texto y proporciona mensajes de error detallados
    si el archivo no puede ser leído. Usa esta herramienta cuando necesites examinar
    el contenido de un solo archivo. Solo funciona dentro de los directorios permitidos.
    
    Args:
        path: La ruta al archivo a leer
    """
    valid_path = await validate_path(path)
    with open(valid_path, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
async def read_multiple_files(paths: List[str]) -> str:
    """Lee el contenido de múltiples archivos simultáneamente.
    
    Esto es más eficiente que leer archivos uno por uno cuando necesitas analizar
    o comparar múltiples archivos. El contenido de cada archivo se devuelve con su
    ruta como referencia. Las lecturas fallidas para archivos individuales no detendrán
    la operación completa. Solo funciona dentro de los directorios permitidos.
    
    Args:
        paths: Lista de rutas de archivos a leer
    """
    results = []
    
    for file_path in paths:
        try:
            valid_path = await validate_path(file_path)
            with open(valid_path, "r", encoding="utf-8") as f:
                content = f.read()
            results.append(f"{file_path}:\n{content}\n")
        except Exception as e:
            results.append(f"{file_path}: Error - {str(e)}")
    
    return "\n---\n".join(results)

@mcp.tool()
async def list_directory(path: str) -> str:
    """Obtiene un listado detallado de todos los archivos y directorios en una ruta especificada.
    
    Los resultados distinguen claramente entre archivos y directorios con prefijos [FILE] y [DIR].
    Esta herramienta es esencial para entender la estructura de directorios y
    encontrar archivos específicos dentro de un directorio. Solo funciona dentro de los directorios permitidos.
    
    Args:
        path: Ruta del directorio a listar
    """
    valid_path = await validate_path(path)
    entries = os.listdir(valid_path)
    formatted = []
    
    for entry in entries:
        entry_path = os.path.join(valid_path, entry)
        is_dir = os.path.isdir(entry_path)
        formatted.append(f"{'[DIR]' if is_dir else '[FILE]'} {entry}")
    
    return "\n".join(formatted)

@mcp.tool()
async def directory_tree(path: str) -> str:
    """Obtiene una vista en árbol recursiva de archivos y directorios como una estructura JSON.
    
    Cada entrada incluye 'name', 'type' (file/directory), y 'children' para directorios.
    Los archivos no tienen array children, mientras que los directorios siempre tienen un array children (que puede estar vacío).
    La salida está formateada con una indentación de 2 espacios para facilitar la lectura. Solo funciona dentro de los directorios permitidos.
    
    Args:
        path: Ruta del directorio raíz para el árbol
    """
    valid_path = await validate_path(path)
    
    async def build_tree(current_path):
        entries = os.listdir(current_path)
        result = []
        
        for entry in entries:
            entry_path = os.path.join(current_path, entry)
            try:
                await validate_path(entry_path)
                is_dir = os.path.isdir(entry_path)
                
                entry_data = {
                    "name": entry,
                    "type": "directory" if is_dir else "file"
                }
                
                if is_dir:
                    entry_data["children"] = await build_tree(entry_path)
                
                result.append(entry_data)
            except ValueError:
                # Skip invalid paths
                continue
        
        return result
    
    tree_data = await build_tree(valid_path)
    return json.dumps(tree_data, indent=2)

@mcp.tool()
async def search_files_tool(path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """Busca recursivamente archivos y directorios que coincidan con un patrón.
    
    Busca a través de todos los subdirectorios desde la ruta de inicio. La búsqueda
    no distingue entre mayúsculas y minúsculas y coincide con nombres parciales. Devuelve rutas completas a todos
    los elementos coincidentes. Excelente para encontrar archivos cuando no conoces su ubicación exacta.
    Solo busca dentro de los directorios permitidos.
    
    Args:
        path: Directorio desde donde comenzar la búsqueda
        pattern: Patrón de texto para buscar en nombres de archivos/directorios
        exclude_patterns: Lista opcional de patrones a excluir de la búsqueda
    """
    valid_path = await validate_path(path)
    results = await search_files(valid_path, pattern, exclude_patterns or [])
    return "\n".join(results) if results else "No se encontraron coincidencias"

@mcp.tool()
async def get_file_info(path: str) -> str:
    """Recupera metadatos detallados sobre un archivo o directorio.
    
    Devuelve información completa incluyendo tamaño, tiempo de creación, tiempo de última modificación, permisos,
    y tipo. Esta herramienta es perfecta para entender las características de un archivo
    sin leer el contenido real. Solo funciona dentro de los directorios permitidos.
    
    Args:
        path: Ruta al archivo o directorio
    """
    valid_path = await validate_path(path)
    info = await get_file_stats(valid_path)
    return "\n".join(f"{key}: {value}" for key, value in info.items())

@mcp.tool()
def list_allowed_directories() -> str:
    """Devuelve la lista de directorios a los que este servidor tiene permiso para acceder.
    
    Usa esto para entender qué directorios están disponibles antes de intentar acceder a los archivos.
    """
    return f"Directorios permitidos:\n{os.linesep.join(allowed_directories)}"

@mcp.tool()
def sequentialthinking(
    thought: str,
    thoughtNumber: int,
    totalThoughts: int,
    nextThoughtNeeded: bool,
    isRevision: Optional[bool] = None,
    revisesThought: Optional[int] = None,
    branchFromThought: Optional[int] = None,
    branchId: Optional[str] = None,
    needsMoreThoughts: Optional[bool] = None
) -> str:
    """Una herramienta detallada para la resolución dinámica y reflexiva de problemas a través de pensamientos.
    
    Esta herramienta ayuda a analizar problemas mediante un proceso de pensamiento flexible que puede adaptarse y evolucionar.
    Cada pensamiento puede basarse en, cuestionar o revisar perspectivas previas a medida que se profundiza la comprensión.
    
    Cuándo usar esta herramienta:
    - Desglosar problemas complejos en pasos
    - Planificación y diseño con espacio para revisión
    - Análisis que podría necesitar corrección de rumbo
    - Problemas donde el alcance completo podría no estar claro inicialmente
    - Problemas que requieren una solución de múltiples pasos
    - Tareas que necesitan mantener contexto a lo largo de múltiples pasos
    - Situaciones donde la información irrelevante debe ser filtrada
    
    Args:
        thought: Tu paso de pensamiento actual
        thoughtNumber: Número actual en la secuencia (puede ir más allá del total inicial si es necesario)
        totalThoughts: Estimación actual de pensamientos necesarios (puede ajustarse hacia arriba/abajo)
        nextThoughtNeeded: Si se necesita otro paso de pensamiento
        isRevision: Si esto revisa un pensamiento previo
        revisesThought: Qué pensamiento está siendo reconsiderado
        branchFromThought: Número de pensamiento del punto de ramificación
        branchId: Identificador de rama
        needsMoreThoughts: Si se necesitan más pensamientos
    """
    input_data = {
        'thought': thought,
        'thoughtNumber': thoughtNumber,
        'totalThoughts': totalThoughts,
        'nextThoughtNeeded': nextThoughtNeeded
    }
    
    # Add optional parameters if provided
    if isRevision is not None:
        input_data['isRevision'] = isRevision
    if revisesThought is not None:
        input_data['revisesThought'] = revisesThought
    if branchFromThought is not None:
        input_data['branchFromThought'] = branchFromThought
    if branchId is not None:
        input_data['branchId'] = branchId
    if needsMoreThoughts is not None:
        input_data['needsMoreThoughts'] = needsMoreThoughts
    
    response = thinking_server.process_thought(input_data)
    return json.dumps(response, indent=2)

# Run the server
if __name__ == "__main__":
    print("Servidor de Sistema de Archivos MCP Seguro con Pensamiento Secuencial en ejecución", file=sys.stderr)
    print(f"Directorios permitidos: {allowed_directories}", file=sys.stderr)
    mcp.run(transport='stdio')