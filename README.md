# Monitor de Seguimiento de Descargas Atmosféricas

Demo del tablero de CEN&T para analizar el riesgo por rayos sobre una red
eléctrica. Cruza el histórico de descargas atmosféricas con el
inventario de estructuras y responde, para un período y un radio dados, qué
estructuras fueron alcanzadas, cuándo y con qué intensidad.

Backend en **FastAPI** (Python 3.11), frontend estático sin framework
(HTML + CSS + JavaScript, con Leaflet para los mapas y Chart.js para las
gráficas).

> ### Los datos de la red son ficticios
>
> Este repositorio es la **versión demo**, pensada para mostrarse en público. La
> red eléctrica que se ve en el mapa no existe:
>
> - **Los nombres son inventados.** Campos, locaciones, circuitos y tags de
>   estructura salen de un diccionario de reemplazo (`scripts/nombres_demo.py`):
>   BOREAL, AUSTRAL, N1…N6 en lugar de los reales.
> - **El trazado está redibujado.** Las coordenadas reales delatan el activo
>   aunque los nombres cambien: basta ubicar la zona en el mapa satelital para
>   reconocerlo. `scripts/geometria_demo.py` tiende una red con **otra forma**,
>   en otra ventana de coordenadas.
>
> Lo que **sí es real** son las descargas atmosféricas: fecha, hora, coordenada,
> corriente y polaridad del histórico del pipeline. La red ficticia se colocó
> dentro de una región con actividad eléctrica medida, para que el demo muestre
> impactos de verdad sobre estructuras que no existen. Lo real y lo inventado se
> cruzan igual que en el tablero original: misma forma estadística, mismo número
> de estructuras, mismo reparto de DPS/DSD.
>
> Los Excel reales viven en `datos/_fuente/`, fuera de git.

---

## Qué se puede hacer

El tablero tiene cuatro vistas, todas gobernadas por los mismos filtros del
panel izquierdo (ubicación, radio de búsqueda y rango de fechas):

| Vista | Para qué sirve |
|---|---|
| **Mapa** | Vista satelital con las estructuras y las descargas del período. Alterna entre mapa general y mapa de calor, y colorea cada rayo según su corriente. |
| **Datos** | Gráficas y tablas del período: distribución por circuito, por tipo de estructura y por presencia de protección (DPS/DSD). Exporta el informe a Excel. |
| **Calendario** | Rejilla mensual con la intensidad de cada día. Al pasar el cursor por un día con actividad aparece una tarjeta con el detalle (descargas, estructuras impactadas, hora pico, corriente máxima y la distribución por hora); al hacer clic queda fija. |
| **Simulador de Tormenta** | Reproduce la caída de los rayos sobre el mapa en orden cronológico, con ambiente meteorológico (sol, lluvia, tormenta), línea de tiempo navegable y la cronología completa en tabla. |

---

## Fuentes de datos

| Archivo | Contenido | ¿En git? |
|---|---|---|
| `datos/Inventario_Estructuras_y_DPS_Final.xlsx` | Inventario de estructuras: coordenadas, circuito, tipo de apoyo y equipos de protección (DPS, DSD, cable de guarda, puesta a tierra). **759 estructuras.** | Sí, y **tiene que estarlo**: no está en Supabase, este repositorio es su única fuente. Es el del demo (nombres ficticios, trazado redibujado) |
| `datos/Localizaciones_Final.xlsx` | Maestro de localizaciones. Define la jerarquía de filtros Campo → Locación/Circuito → Pórtico/Tramo. | Sí, igual que el anterior |
| `datos/Gold_Consolidado_Historico_Descargas_Electricas_GPK.parquet` | Histórico de descargas (fecha, hora, coordenadas, corriente, polaridad, error de localización): ~782 mil registros desde 2021. Copia del Gold del pipeline. | **No: solo local** |

Las descargas de **producción salen siempre de Supabase**. El parquet es una copia
local de los mismos datos reales, **solo para trabajar en tu máquina**: pruebas,
optimizaciones y mejoras del tablero sin gastar egress. No está en git ni en la
imagen de Docker, así que producción no puede usarlo ni por error.

### Elegir de dónde salen las descargas

La variable `FUENTE_DATOS` decide la fuente, y el tablero muestra una etiqueta
que la nombra.

| `FUENTE_DATOS` | Dónde | Etiqueta | Cómo funciona |
|---|---|---|---|
| `parquet` | Solo local (valor por defecto de `docker-compose.yml`) | **Data Local (Parquet)** | Lee `datos/…parquet`. **Nunca se conecta a Supabase**, aunque la URL esté configurada. Si el archivo se reemplaza, lo toma sin reiniciar. |
| `supabase` | Producción (valor por defecto de la imagen) | **Base de datos (Supabase)** | Arranca desde la foto de su caché guardada en la base y baja solo los días nuevos (ver [Producción](#producción-render)). Responde desde memoria y revisa cambios como máximo una vez por minuto mientras alguien usa el tablero. Requiere `SUPABASE_DASHBOARD_DB_URL`. |

Si Supabase no responde:
- **Al arrancar, sin datos todavía:** las consultas responden 503 con *"Sin conexión
  con la base de datos. Se reintenta en menos de un minuto."* No se muestra un
  tablero con cero descargas, que parecería un dato real.
- **Con datos ya cargados:** sigue sirviéndolos y la etiqueta lo avisa (*"Sin
  conexión con la base · datos hasta …"*).

### Generar o actualizar el parquet local

Copia el Gold que genera el pipeline, sin tocar Supabase (definir
`RUTA_GOLD_PIPELINE` en `.env`):

```bash
python scripts/actualizar_parquet.py
```

El script valida el archivo antes de reemplazarlo (esquema, que no traiga menos
del 95 % de las filas ni fechas más viejas) y lo reemplaza de forma atómica. **No
se commitea.** Los Excel se actualizan reemplazando el archivo con el mismo nombre;
el backend detecta el cambio por la fecha de modificación.

> Los pórticos se identifican por el par `circuito␟tag`, no por el tag suelto:
> el tag `PORT` se repite en varias locaciones y por sí solo no distingue nada.

### Regenerar los Excel del demo

Solo hace falta si cambian los Excel reales. Lee de `datos/_fuente/` (la copia
intacta, fuera de git) y escribe sobre `datos/`:

```bash
python scripts/generar_datos_demo.py
```

Lee de una copia y no del archivo que va a pisar a propósito: así se puede
correr las veces que haga falta y da siempre lo mismo. Al terminar verifica solo,
y falla si algo no cuadra: que los dos archivos sigan cruzando igual, que no
sobreviva ninguna palabra de la lista negra y que no cambie el número de
estructuras ni el reparto de DPS/DSD.

> **Antes de commitear un cambio en esos dos Excel**, comprobar que son los
> anonimizados: en la columna `CAMPO` tiene que ir `BOREAL`/`AUSTRAL`, no los
> nombres reales.

---

## Correr en local

Requiere Docker Desktop. **Doble clic en `Iniciar_Dashboard.bat`** y elegir en el
menú de dónde salen los datos:

| Opción | Fuente | Cuándo usarla |
|---|---|---|
| **1. Parquet** | El archivo local de `datos/` | Pruebas y mejoras. Arranca en segundos y no gasta egress. Si falta el parquet, el lanzador lo dice y explica cómo generarlo. |
| **2. Base de datos** | Supabase, igual que producción | Comprobar el comportamiento real. Pide confirmación porque **consume egress**: ~0,75 MB por arranque con foto, ~3,9 MB sin ella. |
| **3. Detener** | — | Apaga el contenedor. |

El lanzador abre Docker Desktop si estaba cerrado, levanta el contenedor
`GPK_Tablero_Web_Demo`, comprueba que el tablero responda de verdad y abre
**http://localhost:8082** en el navegador.

La lógica está en `iniciar_dashboard.ps1`, que también se puede llamar desde una
terminal saltándose el menú:

```bash
powershell -ExecutionPolicy Bypass -File .\iniciar_dashboard.ps1 -Fuente parquet
powershell -ExecutionPolicy Bypass -File .\iniciar_dashboard.ps1 -Detener
```

Añadir `-Reconstruir` solo si cambió el `Dockerfile` o `requirements.txt`.

A mano, sin lanzador, es el `docker compose` de siempre:

```bash
docker compose up --build -d
docker compose down
```

`docker-compose.yml` es solo para desarrollo: monta el código como volumen y
arranca uvicorn con `--reload`, así los cambios se ven sin reconstruir la imagen.
El despliegue en Render **no** usa este archivo, sino el `Dockerfile`.

---

## Pruebas

Ninguna prueba se conecta a Supabase ni gasta egress: el papel de la base lo
cumple un Supabase simulado sobre el parquet local, que tiene los mismos datos que
el Gold. Si el parquet no existe, las pruebas que lo necesitan se saltan diciendo
cómo generarlo.

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

Cubren:
- **Sincronización con la base:** arranque desde cero, días nuevos, recargados o
  borrados, caídas al arrancar y recuperación.
- **La foto de la caché** (`tests/test_foto.py`): formato y exactitud de las
  huellas, arranque con foto sin bajar filas, foto vieja o de otra zona, fallos al
  guardar y base sin la tabla de la foto.
- **Respuestas idénticas byte a byte** entre el modo parquet y el modo Supabase,
  arrancando desde cero y desde la foto.
- Las consultas sobre los datos en memoria y el script de actualización del parquet.

Dos pruebas de carga se corren a mano:

```bash
python tests/prueba_carga.py http://127.0.0.1:8000 10
```

Con el servidor ya levantado, simula 10 usuarios usándolo a la vez sin pausas.

```bash
python tests/simular_render.py 10
```

Solo en Windows: levanta el servidor con 0,1 de CPU, como el plan Free de
Render, corre la prueba de carga y reporta el pico de memoria contra los 512 MB.

---

## Producción (Render)

Producción vive en Render, se construye con el `Dockerfile` (no con
`docker-compose.yml`) y **se despliega sola con cada push a `main`**
(`autoDeploy: true` en `render.yaml`).

### Variables del panel de Render

Se cargan en *Environment*, no en un archivo, porque la URL es un secreto:

| Variable | Valor | Por qué |
|---|---|---|
| `SUPABASE_DASHBOARD_DB_URL` | URL del usuario `dashboard_readonly`, Transaction pooler (puerto 6543) | Sin ella la imagen **se niega a arrancar**. |
| `FUENTE_DATOS` | `supabase` | Ya es el valor por defecto de la imagen; dejarla explícita evita sorpresas. |
| `FOTO_ID` | `2` | La fila de la foto de caché de este demo. La `1` es la del tablero de producción, que corre contra la misma base (ver [Dos tableros, una base](#dos-tableros-una-base)). Ya es el valor por defecto de la imagen. |

`PORT` lo inyecta Render y el `Dockerfile` ya lo usa.

### La foto de la caché

Render Free borra la memoria cada vez que el servicio se duerme (15 minutos sin
tráfico), se redespliega o se reinicia, y no tiene discos persistentes. Sin nada
más, cada arranque en frío le pediría a Supabase todas las descargas de la zona
de las estructuras. Para evitarlo, el tablero guarda en la propia base una **foto
comprimida de su caché** (`backend/foto.py`, ~450 KB) y la lee al despertar:

```
Despierta ─► lee los datos de la foto (unos bytes)
              ├─ sirve (mismo formato, su zona cubre la actual)
              │     └─► la descarga ─► compara huellas con Supabase
              │                          ├─ iguales: listo, 0 filas
              │                          └─ el pipeline publicó después: baja solo esos días
              └─ no sirve o no hay ─► arma todo desde las filas
Si los datos cambiaron, guarda una foto nueva en segundo plano (subir no gasta egress).
```

Medido el 2026-09-16 con la imagen de producción (512 MB, 0,1 de CPU):

| Arranque | Contra Supabase real | Contra Postgres local |
|---|---|---|
| Sin foto | 3.867 KB | 3.332 KB |
| Con foto, el pipeline publicó después | — | 619 KB (bajó solo 3 días) |
| **Con foto al día** | **752 KB** | **607 KB** (0 filas) |
| Revisión de cada minuto | — | 458 bytes |

Con 10 arranques al día son ~225 MB al mes de los 5 GB del plan, frente a ~1,2 GB
sin foto. Con 10 usuarios a la vez el tablero no gasta egress (responde desde
memoria) y el pico de memoria medido fue de 432 MB de 512.

La foto es prescindible: si está corrupta, es de otro formato, falla al guardarse
o la tabla no existe, el tablero arma la caché desde las filas y sigue funcionando.
Se puede borrar la fila sin perder datos; el próximo arranque la vuelve a armar.

El tamaño de la foto crece con el histórico: los 450 KB medidos el 2026-09-16
eran 618 KB el 2026-10-22, con 1.475 días de datos.

### Dos tableros, una base

Este demo y el tablero de producción leen la **misma** base de Supabase, y la
tabla de la foto que crea `sql/001_foto_tablero.sql` tiene **una sola fila**
(`id = 1`). Eso no alcanza para los dos, porque sus zonas no son compatibles: el
demo redibujó la red en otra ventana de coordenadas, y una foto solo sirve si su
caja **cubre** la zona que se está pidiendo.

| | lat | lon |
|---|---|---|
| Producción (red real) | 4,3180 – 4,5409 | −72,8205 – −72,5029 |
| Demo (red redibujada) | 4,4905 – 4,6909 | −72,9834 – −72,6871 |

Se solapan en parte, pero ninguna contiene a la otra. Compartiendo la fila, cada
tablero encontraría la foto del otro, la descartaría, armaría su caché desde las
filas (~3,4 MB) y la pisaría; el siguiente arranque del otro repetiría el ciclo.
Los dos quedarían **sin foto útil para siempre**, y el egress de cada uno pasaría
de ~225 MB a ~1,2 GB al mes sobre los 5 GB del plan.

`sql/002_foto_por_tablero.sql` le da una fila a cada uno (`FOTO_ID`): `1`
producción, `2` este demo, `3`–`9` libres. **Producción no se toca**: la función
de 4 argumentos del 001 sigue existiendo y escribiendo la fila 1, y su tablero
lee con `WHERE id = 1`, así que nunca ve la fila del demo. No hay que
redesplegarlo ni cambiar su código.

Si el 002 no está aplicado, el demo funciona igual: no encuentra foto para su
fila, arma la caché desde las filas, y al intentar guardarla falla sin
consecuencias (guardar corre en segundo plano y se reintenta). **No pisa la de
producción en ningún caso.**

### Preparar la base (una sola vez)

Dos scripts, en el *SQL Editor* de Supabase y con el usuario `postgres`. Los dos
son idempotentes: correrlos de nuevo no borra las fotos.

| Script | Para qué | Estado |
|---|---|---|
| `sql/001_foto_tablero.sql` | Tabla y función de la foto | Aplicado el 2026-09-16 |
| `sql/002_foto_por_tablero.sql` | Una fila por tablero, para que el demo no le pise la foto a producción | **Aplicar antes de desplegar el demo** |

El usuario del tablero **sigue sin poder escribir ninguna tabla**: recibe `SELECT`
sobre la foto y permiso para ejecutar `guardar_foto_tablero()`, que solo reemplaza
esa fila. Incluye una política de lectura explícita, porque con RLS y sin
política el usuario vería cero filas sin ningún error.

Para comprobar que está bien aplicado:

```sql
SELECT
  to_regclass('public.gpk_tablero_foto')                                   AS tabla,
  has_function_privilege('dashboard_readonly',
    'public.guardar_foto_tablero(smallint,jsonb,text,bytea)', 'EXECUTE')  AS puede_guardar_001,
  has_function_privilege('dashboard_readonly',
    'public.guardar_foto_tablero(smallint,smallint,jsonb,text,bytea)', 'EXECUTE') AS puede_guardar_002,
  has_table_privilege('dashboard_readonly', 'public.gpk_tablero_foto', 'INSERT') AS tablero_puede_insertar,
  has_table_privilege('anon', 'public.gpk_tablero_foto', 'SELECT')        AS anon_puede_leer,
  (SELECT count(*) FROM pg_policies WHERE tablename = 'gpk_tablero_foto')  AS politicas;
```

Resultado esperado: `gpk_tablero_foto | true | true | false | false | 1`.

Y para ver qué tablero tiene foto guardada, sin descargar ninguna:

```sql
SELECT id, bytes, generada_en, caja FROM public.gpk_tablero_foto ORDER BY id;
```

### Antes de desplegar

```bash
python -m pytest tests
```

---

## Estructura del proyecto

```
├── backend/
│   ├── main.py          API FastAPI: cruce espacial, filtros y endpoints
│   ├── datos.py         Fuente de datos (parquet o Supabase) y sincronización
│   ├── foto.py          Foto de la caché que se guarda en la base
│   ├── lectura_parquet.py  Lectura del parquet en un proceso aparte
│   ├── db.py            Conexión a Supabase con el usuario del tablero
│   └── informe.py       Generación del informe en Excel
├── datos/
│   ├── Inventario_Estructuras_y_DPS_Final.xlsx   Estructuras del demo (en git)
│   ├── Localizaciones_Final.xlsx                 Maestro del demo (en git)
│   ├── _fuente/             Los Excel REALES. No están en git
│   └── Gold_…parquet        Solo local, no está en git (scripts/actualizar_parquet.py)
├── sql/
│   ├── 001_foto_tablero.sql     Tabla y función de la foto (aplicado en Supabase)
│   └── 002_foto_por_tablero.sql Una fila de foto por tablero (FOTO_ID)
├── scripts/
│   ├── actualizar_parquet.py   Copia el Gold del pipeline como parquet local
│   ├── generar_datos_demo.py   Arma los Excel del demo desde datos/_fuente/
│   ├── geometria_demo.py       Redibuja la red: otro trazado, misma zona de rayos
│   └── nombres_demo.py         Diccionario de nombres y tags ficticios
├── tests/               Pruebas (pytest) y pruebas de carga manuales
├── static/
│   ├── index.html       Estructura del tablero (las cuatro vistas)
│   ├── script.js        Toda la lógica del frontend
│   ├── styles.css       Estilos, escala adaptativa y temas
│   ├── logo-cent.png / logo-cent-negativo.png
│   └── favicon.png
├── Iniciar_Dashboard.bat    Doble clic: menú para levantar el tablero
├── iniciar_dashboard.ps1    Lógica del lanzador (Windows)
├── Dockerfile           Imagen de producción (la que usa Render)
├── docker-compose.yml   Entorno de desarrollo local (contenedor GPK_Tablero_Web_Demo)
├── render.yaml          Blueprint del despliegue
└── requirements.txt     Dependencias con versiones fijadas
```

> El pipeline que alimenta este tablero vive en el repositorio aparte
> `Web_Scraping_Visor_Descargas_Atmosfericas`: Airflow scrapea, arma
> Bronze → Silver → Gold y publica el Gold en Supabase. Se levanta con su propio
> `Iniciar_Orquestador_Airflow.bat` y su interfaz queda en
> http://localhost:8081.


