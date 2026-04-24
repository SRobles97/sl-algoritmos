# sl-analytics

Entorno local para prototipar análisis. Te conecta a la base de datos de producción (TimescaleDB en el VPS), trae los datos a un notebook de Jupyter como DataFrames de pandas y te permite probar algoritmos en tu máquina antes de pasarlos a producción.

**Estás conectado a la base de datos de producción. Por favor, solo lectura (SELECT).** Cualquier proceso que deba ejecutarse en producción, avísame junto con la entrega (ver más abajo).

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y abierto
- [Visual Studio Code](https://code.visualstudio.com/)
- La extensión [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) de VS Code
- Un archivo `.env` con las credenciales entregadas por privado. **Nunca lo subas a git.**

## Instalación

```bash
git clone <url-del-repo> sl-analytics
cd sl-analytics
cp .env.example .env
```

Completa los valores de `.env` con las credenciales que te compartí.

Luego abre la carpeta en VS Code:

1. Abre Docker Desktop y espera a que quede corriendo.
2. En VS Code, abre la carpeta `sl-analytics`.
3. Cuando VS Code pregunte, elige **Reopen in Container**.
4. Si no aparece el aviso, abre la paleta de comandos (`Cmd+Shift+P`) y ejecuta **Dev Containers: Reopen in Container**.

Listo. El contenedor instala Python, dependencias y el paquete local automáticamente.

## Prueba rápida de conexión

```bash
python scripts/test_connection.py
```

Debería imprimir una fila con la versión de PostgreSQL y la hora actual del VPS. Si esto funciona, todo lo demás funciona.

## Uso del notebook

```bash
jupyter notebook notebooks/01-exploration.ipynb
```

La API tiene dos funciones:

```python
from sl_analytics.db import query, get_engine

# Caso del 90%: SQL → DataFrame
df = query("SELECT * FROM devices LIMIT 10")

# Con parámetros
df = query(
    "SELECT day, load_minutes FROM device_daily_facts WHERE device_id = :d",
    {"d": 1},
)

# Escape: motor de SQLAlchemy directo, para to_sql, ORM, operaciones masivas, etc.
engine = get_engine()
```

El túnel SSH se abre automáticamente la primera vez que llamas a `query()` y se cierra solo cuando apagas el kernel. No tienes que preocuparte por él.

## Flujo de entrega (David -> Sebastián)

Cuando un algoritmo esté listo para pasar a producción:

1. Crea una carpeta `notebooks/handoffs/<tema>/` (la palabra "handoff" significa "entrega") con:
   - `README.md` — qué hace el algoritmo, por qué, qué espera de entrada y de salida, casos límite que detectaste
   - Las consultas SQL relevantes en archivos `.sql` separados
   - Un archivo `.py` pequeño con la(s) función(es) principal(es), pura(s), sin llamadas a la base dentro (la I/O queda en el notebook)
   - Una muestra del DataFrame (`.parquet` o `.csv`) para que pueda validar el comportamiento sin tener que volver a ejecutar la consulta
2. Avisar por wsp con un enlace a la carpeta.

## Referencia del esquema

La referencia completa de tablas, columnas y relaciones está en [`docs/esquema.md`](docs/esquema.md). Tablas que probablemente usarás:

- `devices`, `companies`
- `power_measurements` (hipertabla de TimescaleDB, columna `time`)
- `device_state_intervals` (intervalos LOAD/OFF)
- `device_daily_facts` (agregados diarios pre-calculados)

Las marcas de tiempo están en zona horaria **`America/Santiago`** (UTC-3).
