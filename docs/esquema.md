# Esquema de la base `centineldb`

Referencia simplificada de las tablas disponibles para consultar. Solo incluye columnas, tipos y relaciones — sin triggers, índices, ni constraints internas.

Zona horaria de los `timestamptz`: **`America/Santiago`** (UTC-3). Cuando filtres por fechas concretas (por ejemplo `>= '2026-03-03 00:00:00-03'`), usa explícitamente el offset, no `CURRENT_DATE`.

---

## Tablas por caso de uso

| ¿Qué buscas? | Tabla principal |
|---|---|
| Lista de dispositivos (máquinas) | [`devices`](#devices) |
| Lectura de energía cruda (sensores) | [`power_measurements`](#power_measurements) |
| Intervalos LOAD / OFF ya calculados | [`device_state_intervals`](#device_state_intervals) |
| Estado actual de cada dispositivo | [`device_current_status`](#device_current_status) |
| Totales diarios pre-calculados | [`device_daily_facts`](#device_daily_facts) |
| Totales diarios por clasificación | [`device_daily_classification_facts`](#device_daily_classification_facts) |
| Horarios de trabajo efectivos | [`device_schedules`](#device_schedules) |
| Clasificaciones (motivos de parada) | [`classifications`](#classifications) |
| Umbrales de histéresis por dispositivo | [`device_power_state_config`](#device_power_state_config) |
| Regla "parada permitida" por dispositivo | [`device_threshold_config`](#device_threshold_config) |

---

## `companies`
Empresa / cliente. Cada dispositivo pertenece a una empresa.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Identificador |
| `name` | `text` | Nombre |
| `slug` | `text` | Clave canónica (lowercase + guiones) |
| `description` | `text` | Descripción opcional |
| `is_active` | `boolean` | Empresa activa |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

---

## `devices`
Dispositivo físico (máquina) que envía mediciones.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Identificador |
| `company_id` | `bigint` FK → `companies.id` | Empresa dueña |
| `device_key` | `text` | Clave externa (ej. `"1101"`, `"Rep44"`) |
| `device_code` | `integer` | Código numérico opcional |
| `display_name` | `text` | Nombre mostrado |
| `is_active` | `boolean` | Dispositivo activo |
| `timezone` | `text` | Zona horaria local del dispositivo (ej. `America/Santiago`) |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Única: `(company_id, device_key)`.

---

## `device_metadata`
Metadata libre en JSON por dispositivo (1-a-1 con `devices`).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `device_id` | `bigint` FK → `devices.id`, único | |
| `data` | `jsonb` | Metadata arbitraria |
| `updated_at` | `timestamptz` | |

---

## `device_power_state_config`
Umbrales de histéresis usados para construir intervalos LOAD/OFF a partir de `power_measurements`. Una fila por dispositivo.

| Columna | Tipo | Descripción |
|---|---|---|
| `device_id` | `bigint` PK, FK → `devices.id` | |
| `on_threshold_w` | `real` | Watts para pasar a LOAD (ej. 500) |
| `off_threshold_w` | `real` | Watts para pasar a OFF (ej. 430). Siempre `< on_threshold_w` |
| `min_state_seconds` | `integer` | Debounce opcional (0 = sin debounce) |
| `power_column` | `text` | Columna de `power_measurements` que se evalúa. Default `'total_active_power'`. Alternativas: `'total_current'`, `'total_apparent_power'` |
| `updated_at` | `timestamptz` | |

---

## `device_threshold_config`
Regla "parada permitida": una parada OFF se marca `is_allowed=true` si su duración es ≤ `duration_minutes`.

| Columna | Tipo | Descripción |
|---|---|---|
| `device_id` | `bigint` PK, FK → `devices.id` | |
| `duration_minutes` | `integer` | Default 15 |
| `updated_at` | `timestamptz` | |

---

## `device_schedules`
Horarios de trabajo efectivos por dispositivo. Varias filas por dispositivo, con vigencia por rango de fechas (no se solapan).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `device_id` | `bigint` FK → `devices.id` | |
| `valid_from` | `date` | Inicio de vigencia (inclusivo) |
| `valid_to` | `date` | Fin de vigencia (inclusivo). `NULL` = indefinido |
| `day_schedules` | `jsonb` | Horarios por día de la semana |
| `extra_hours` | `jsonb` | Horas extra |
| `special_days` | `jsonb` | Días especiales (feriados, etc.) |
| `version` | `text` | Default `'1.0'` |
| `source` | `text` | Default `'ui'` |
| `valid_range` | `daterange` (generada) | Para consultas de vigencia |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

---

## `classifications`
Clasificaciones (motivos de parada / tipos de trabajo) configurables por empresa.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `company_id` | `bigint` FK → `companies.id` | |
| `name` | `text` | |
| `description` | `text` | |
| `status` | `text` | `'active'` por defecto |
| `color` | `text` | Color hex para UI (ej. `'#9E9E9E'`) |
| `is_work` | `boolean` | Si esta clasificación cuenta como trabajo |
| `is_system` | `boolean` | Creada automáticamente |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Única: `(company_id, name)`.

---

## `power_measurements`
**Hipertabla de TimescaleDB.** Lecturas crudas de energía por dispositivo, varias por minuto.

| Columna | Tipo | Descripción |
|---|---|---|
| `time` | `timestamptz` | Timestamp de la lectura (clave de particionado) |
| `device_id` | `bigint` FK → `devices.id` | |
| `company_id` | `bigint` FK → `companies.id` | Denormalizado para filtrar rápido |
| `phase_a_current` / `phase_b_current` / `phase_c_current` | `real` | Corriente por fase |
| `phase_a_voltage` / `phase_b_voltage` / `phase_c_voltage` | `real` | Tensión por fase |
| `phase_a_active_power` / `phase_b_active_power` / `phase_c_active_power` | `real` | Potencia activa por fase |
| `phase_a_apparent_power` / `phase_b_apparent_power` / `phase_c_apparent_power` | `real` | Potencia aparente por fase |
| `phase_a_power_factor` / `phase_b_power_factor` / `phase_c_power_factor` | `real` | Factor de potencia por fase |
| `phase_a_frequency` / `phase_b_frequency` / `phase_c_frequency` | `real` | Frecuencia por fase |
| `total_current` | `real` | Corriente total |
| `total_active_power` | `real` | Potencia activa total (columna por defecto para histéresis) |
| `total_apparent_power` | `real` | Potencia aparente total |

Única: `(time, device_id)` para idempotencia.

---

## `discrete_measurements`
**Hipertabla de TimescaleDB.** Señales discretas (entradas digitales).

| Columna | Tipo | Descripción |
|---|---|---|
| `time` | `timestamptz` | |
| `device_id` | `bigint` FK → `devices.id` | |
| `company_id` | `bigint` FK → `companies.id` | |
| `d1_state` / `d2_state` / `a1_state` | `integer` | Estados discretos |

Única: `(time, device_id)`.

---

## `device_state_intervals`
Intervalos LOAD / OFF derivados de `power_measurements`. Esta es probablemente la tabla principal para análisis.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `device_id` | `bigint` FK → `devices.id` | |
| `source` | `text` | `'power'` o `'discrete'`. Default `'power'` |
| `state` | `text` | `'LOAD'` o `'OFF'` |
| `start_time` | `timestamptz` | Inicio del intervalo |
| `end_time` | `timestamptz` | Fin del intervalo. `NULL` = intervalo abierto (todavía en ejecución) |
| `duration_seconds` | `bigint` | Calculada automáticamente al cerrar |
| `measurement_count` | `integer` | Cantidad de lecturas dentro del intervalo |
| `classification_id` | `bigint` FK → `classifications.id` | Clasificación asignada (solo para OFF) |
| `is_allowed` | `boolean` | `true` si es OFF y dura ≤ `device_threshold_config.duration_minutes` |
| `on_schedule_seconds` | `bigint` | Segundos del intervalo que caen dentro del horario de trabajo |
| `on_schedule_ratio` | `real` | Proporción dentro del horario (0.0 a 1.0) |
| `on_schedule` | `boolean` | Si el intervalo se considera "en horario" según la regla |
| `on_schedule_rule` | `text` | Regla aplicada: `'strict'`, `'any'` o `'majority'` (por defecto) |
| `schedule_computed_at` | `timestamptz` | Cuándo se calcularon los campos `on_schedule_*` |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

**Reglas importantes**
- LOAD siempre se crea cuando la potencia supera `on_threshold_w`.
- OFF **solo se crea** dentro del horario de trabajo del dispositivo. Sin horario = no hay intervalos OFF.

---

## `device_current_status`
Caché con el estado actual de cada dispositivo, actualizado por workers. Útil para dashboards en tiempo real.

| Columna | Tipo | Descripción |
|---|---|---|
| `device_id` | `bigint` PK, FK → `devices.id` | |
| `last_power_time` | `timestamptz` | Última lectura de `power_measurements` recibida |
| `last_discrete_time` | `timestamptz` | Última lectura de `discrete_measurements` recibida |
| `current_state` | `text` | `'LOAD'`, `'OFF'`, o `'UNKNOWN'` |
| `current_state_since` | `timestamptz` | Cuándo empezó el estado actual |
| `open_interval_id` | `bigint` FK → `device_state_intervals.id` | Intervalo abierto actual |
| `on_schedule` | `boolean` | Si el dispositivo está en horario de trabajo ahora |
| `shift_start` / `shift_end` | `time` | Turno actual |
| `total_schedule_minutes` | `integer` | Minutos totales programados hoy |
| `worked_minutes` | `real` | Minutos trabajados hoy |
| `active_minutes` | `real` | Minutos activos hoy |
| `duration_minutes` | `real` | Duración del estado actual |
| `is_classified` | `boolean` | Si el intervalo actual tiene clasificación |
| `allowed_stoppage` | `boolean` | Si la parada actual está dentro del límite permitido |
| `is_stale` | `boolean` | Si la caché está desactualizada |
| `is_on` | `boolean` | Si el dispositivo está encendido |
| `computed_at` | `timestamptz` | Cuándo se calculó este snapshot |

---

## `device_daily_facts`
Agregados diarios por dispositivo. La tabla más eficiente para reportes día/semana/mes.

| Columna | Tipo | Descripción |
|---|---|---|
| `device_id` | `bigint` PK-parcial, FK → `devices.id` | |
| `day` | `date` PK-parcial | Día local del dispositivo |
| `total_minutes` | `real` | Total del día |
| `load_minutes` | `real` | Minutos en LOAD |
| `load_minutes_on_schedule` | `real` | LOAD dentro del horario |
| `load_minutes_off_schedule` | `real` | LOAD fuera del horario |
| `off_minutes` | `real` | Minutos en OFF |
| `off_minutes_on_schedule` | `real` | OFF dentro del horario |
| `off_minutes_off_schedule` | `real` | OFF fuera del horario |
| `allowed_off_minutes` | `real` | Minutos OFF que caen dentro del límite permitido |
| `allowed_off_minutes_on_schedule` | `real` | |
| `allowed_off_minutes_off_schedule` | `real` | |
| `interval_count` | `integer` | Total de intervalos del día |
| `load_interval_count` | `integer` | Intervalos LOAD |
| `off_interval_count` | `integer` | Intervalos OFF |
| `allowed_off_interval_count` | `integer` | Intervalos OFF permitidos |
| `kwh` | `double precision` | Energía consumida en el día |
| `measurement_count` | `integer` | Total de lecturas recibidas |
| `computed_at` | `timestamptz` | Cuándo se calculó |

PK: `(device_id, day)`.

---

## `device_daily_classification_facts`
Agregados diarios por clasificación (permite desglosar paradas por motivo).

| Columna | Tipo | Descripción |
|---|---|---|
| `device_id` | `bigint` PK-parcial, FK → `devices.id` | |
| `day` | `date` PK-parcial | |
| `classification_id` | `bigint` PK-parcial, FK → `classifications.id` | `NULL` = "Sin asignar" |
| `state` | `text` PK-parcial | Default `'OFF'` |
| `minutes` | `real` | Minutos totales |
| `minutes_on_schedule` | `real` | Dentro del horario |
| `minutes_off_schedule` | `real` | Fuera del horario |
| `interval_count` | `integer` | |
| `computed_at` | `timestamptz` | |

PK: `(device_id, day, classification_id, state)`.

---

## Tablas de autenticación / tenant

Probablemente no las necesites para análisis, pero están:

- **`users`** — usuarios del sistema (email, hashed_password, etc.)
- **`company_users`** — rol por empresa (viewer/admin)
- **`company_api_keys`** — API keys por empresa
- **`company_aliases`** — nombres alternativos de empresas (para normalizar payloads)
- **`refresh_tokens`** — tokens de refresh de sesión
- **`audit_logs`** — registro de acciones de usuarios

---

## Mapa rápido de relaciones

```
companies
├── company_aliases
├── company_users ── users
├── company_api_keys
├── audit_logs ── users
├── classifications
└── devices
    ├── device_metadata
    ├── device_power_state_config
    ├── device_threshold_config
    ├── device_schedules
    ├── power_measurements         (hipertabla)
    ├── discrete_measurements      (hipertabla)
    ├── device_state_intervals ── classifications
    ├── device_current_status ── device_state_intervals
    ├── device_daily_facts
    └── device_daily_classification_facts ── classifications
```

---

## Consultas típicas de referencia

```sql
-- Lista de dispositivos activos de una empresa
SELECT id, device_key, display_name, timezone
FROM devices
WHERE company_id = 1 AND is_active = true
ORDER BY device_key;

-- Intervalos LOAD/OFF de un dispositivo en los últimos 7 días
SELECT state, start_time, end_time, duration_seconds, is_allowed, on_schedule, classification_id
FROM device_state_intervals
WHERE device_id = 1
  AND start_time >= now() - interval '7 days'
ORDER BY start_time;

-- Agregados diarios de un dispositivo en un mes
SELECT day, load_minutes, off_minutes, allowed_off_minutes, kwh
FROM device_daily_facts
WHERE device_id = 1
  AND day BETWEEN '2026-03-01' AND '2026-03-31'
ORDER BY day;

-- Paradas clasificadas por motivo en el mes
SELECT c.name, SUM(f.minutes) AS minutos, SUM(f.interval_count) AS paradas
FROM device_daily_classification_facts f
LEFT JOIN classifications c ON c.id = f.classification_id
WHERE f.device_id = 1
  AND f.day BETWEEN '2026-03-01' AND '2026-03-31'
  AND f.state = 'OFF'
GROUP BY c.name
ORDER BY minutos DESC;

-- Potencia cruda de un dispositivo en las últimas 2 horas
SELECT time, total_active_power
FROM power_measurements
WHERE device_id = 1
  AND time >= now() - interval '2 hours'
ORDER BY time;
```
