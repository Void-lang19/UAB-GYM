# UAB-GYM

Sistema web para apoyar la administración del gimnasio de la Universidad Adventista de Bolivia (UAB), en Vinto, Cochabamba.

## Objetivo

Construir una aplicación administrativa modular para gestionar socios, entrenadores, planes, membresías, pagos y asistencias, con autenticación, permisos y reportes. La interfaz administrativa se desarrollará con Flask-AppBuilder y la base de datos del proyecto será MySQL/MariaDB.

## Tecnologías

- Python 3.10 o superior (el proyecto se está preparando y probando con Python 3.13).
- Flask-AppBuilder 5.3.0.
- SQLAlchemy, gestionado como dependencia de Flask-AppBuilder.
- MySQL/MariaDB de XAMPP.
- PyMySQL como controlador de MySQL.
- Git y GitHub.

## Interfaz

La interfaz usa español latinoamericano y una paleta institucional azul y blanca: `#0474C4`, `#5379AE`, `#FFFFFF`, `#A8C4EC`, `#06457F` y `#262B40`. El tema se aplica a las pantallas administrativas generadas por Flask-AppBuilder, los reportes y el asistente. El acceso tiene un diseño propio y el inicio muestra únicamente los módulos permitidos para la cuenta, en un diseño adaptable a móviles.

## Requisitos previos

1. Instala Python desde [python.org](https://www.python.org/downloads/windows/) y habilita **Add Python to PATH** durante la instalación. Comprueba la instalación en PowerShell:

   ```powershell
   python --version
   ```

2. Instala XAMPP. Abre el panel de control de XAMPP e inicia **MySQL**. No es necesario cambiar la configuración del servidor.
3. Instala Git para Windows y VS Code.

## Configuración inicial en Windows

Los siguientes comandos se ejecutan desde PowerShell en `C:\xampp\htdocs\UAB-GYM`, salvo que se indique lo contrario.

### 1. Clonar el repositorio y cambiar a `develop`

Si todavía no tienes una copia:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd UAB-GYM
git switch develop
```

Si ya tienes el repositorio clonado, abre esa carpeta en PowerShell y actualízala:

```powershell
git switch develop
git pull origin develop
```

### 2. Crear la base de datos

Inicia MySQL desde el panel de XAMPP y abre `http://localhost/phpmyadmin`. Selecciona **Nueva**, escribe `uab_gym` como nombre y elige la intercalación `utf8mb4_unicode_ci`. Esta configuración inicial crea la base vacía; no borres ni reinicies bases existentes.

### 3. Crear y activar el entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, permite scripts locales solo para la sesión actual y vuelve a activarlo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

El prompt debe mostrar `(.venv)`.

### 4. Instalar dependencias

Con el entorno virtual activo:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Configurar las variables locales

```powershell
Copy-Item .env.example .env
```

Edita `.env` y reemplaza `SECRET_KEY` por una clave aleatoria generada con:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copia el resultado en `SECRET_KEY` dentro de `.env`. Ajusta `DB_USER` y `DB_PASSWORD` si tu instalación de MySQL no usa `root` sin contraseña. Nunca subas `.env` a Git; el repositorio ignora ese archivo y mantiene únicamente `.env.example`.

### 6. Crear las tablas iniciales, comprobar la conexión y ejecutar

Con MySQL iniciado y `.env` configurado, crea las tablas de los módulos iniciales:

```powershell
flask --app app:create_app init-db
```

El comando crea las tablas de socios, entrenadores, planes, membresías, pagos y asistencias si todavía no existen; no elimina ni reinicia tablas. Flask-AppBuilder también administra sus tablas internas de seguridad. Los reportes consultan estas tablas y no necesitan tablas adicionales.

Para cargar registros ficticios de prueba en cada módulo:

```powershell
flask --app app:create_app seed-demo
```

Agrega 3 socios, 2 entrenadores, 3 planes, 3 membresías, 4 pagos y 3 asistencias con datos de ejemplo sin etiquetas de demostración en las pantallas. Son datos ficticios para el prototipo; no corresponden a personas ni transacciones reales. La carga no reemplaza otros registros y se puede volver a ejecutar sin duplicar los ejemplos. Úsala solo en una base de desarrollo.

Verifica la conexión a `uab_gym`:

```powershell
flask --app app:create_app check-db
```

La respuesta correcta indica el nombre de la base y la versión de MySQL/MariaDB. Luego inicia el servidor local:

```powershell
flask --app app:create_app run --debug
```

Abre `http://127.0.0.1:5000` en el navegador. Detén el servidor con `Ctrl+C`.

En la primera inicialización, Flask-AppBuilder crea sus tablas internas de seguridad y permisos en `uab_gym`. Antes de utilizar las vistas privadas, crea el primer administrador con el comando de la sección de autenticación.

## CRUD de socios

La sección **Gimnasio → Socios** permite registrar, buscar, consultar y editar socios. Se puede buscar por nombres, apellidos, documento, correo y estado. El documento es obligatorio; el correo, si se proporciona, debe tener formato válido; y la fecha de nacimiento no puede estar en el futuro.

El borrado físico está deshabilitado. Para conservar el historial que necesitarán las membresías, un usuario con permisos puede desactivar socios desde la acción de la tabla o cambiar su estado en el formulario. La pantalla requiere iniciar sesión; la creación de usuarios y la asignación de roles se documentarán en la etapa de autenticación.

## CRUD de entrenadores

La sección **Gimnasio → Entrenadores** permite registrar, buscar, consultar y editar entrenadores. La búsqueda incluye nombres, apellidos, documento, correo, especialidad y estado. Se validan los campos requeridos, el formato del correo y que la fecha de contratación no sea futura.

El borrado físico está deshabilitado; los entrenadores se pueden desactivar sin borrar su información. La lista y sus acciones requieren iniciar sesión.

## CRUD de planes

La sección **Gimnasio → Planes** permite registrar, buscar, consultar y editar planes por nombre, duración, precio, beneficios y estado. La duración se expresa en días y debe ser positiva; el precio puede ser cero, pero no negativo. Los nombres de plan son únicos.

El borrado físico está deshabilitado; los planes pueden desactivarse para conservar la referencia de membresías. La lista y sus acciones requieren iniciar sesión.

## Autenticación y administrador

Flask-AppBuilder proporciona las páginas de inicio y cierre de sesión (`/login/` y `/logout/`) y protege las vistas con permisos. La autenticación configurada es de base de datos, el registro público está deshabilitado, las solicitudes usan CSRF y las cookies de sesión son `HttpOnly` y `SameSite=Lax`.

Con el entorno virtual activo, MySQL iniciado y `.env` configurado, crea el primer usuario administrador de forma interactiva:

```powershell
flask --app app:create_app fab create-admin
```

Responde las preguntas del asistente y escribe la contraseña en el prompt oculto; Flask-AppBuilder la almacenará con hash. No guardes esa contraseña en archivos ni en comandos. El rol `Admin` recibe los permisos administrativos.

El rol interno `Admin` corresponde al rol **ADMINISTRADOR** de la matriz y se conserva sin cambios. Después de crear el administrador, configura de forma idempotente los roles de aplicación:

```powershell
flask --app app:create_app configure-roles
```

El comando crea `Recepcionista` y `Entrenador` si no existen y solo sincroniza sus permisos sobre las vistas actuales; no modifica `Admin`, `Public`, usuarios ni permisos de otros módulos. Después, un administrador puede crear usuarios desde **Seguridad → Usuarios** y asignarles el rol correspondiente.

| Rol | Socios | Entrenadores | Planes |
|---|---|---|---|
| ADMINISTRADOR (`Admin`) | Acceso administrativo completo; el borrado físico sigue deshabilitado | Acceso administrativo completo | Acceso administrativo completo |
| Recepcionista | Listar, consultar, crear, editar y desactivar; sin borrado físico | Listar y consultar | Listar y consultar |
| Entrenador | Sin acceso hasta que exista un filtro verificable por asignación | Sin acceso hasta que exista el vínculo con su perfil | Listar y consultar |

El esquema actual aún no relaciona usuarios con entrenadores ni entrenadores con socios. Por ello, no se concede al rol `Entrenador` acceso a listados que expondrían registros ajenos. Sus vistas de socios, asistencias y reportes deben habilitarse al integrar una relación verificable de asignación. Los permisos de membresías, pagos, asistencias y reportes se detallan en las secciones correspondientes; la IA queda fuera de esta etapa.

Las pruebas de autorización usan una base SQLite temporal y verifican acceso por URL directa, la conservación de permisos de `Admin`, el alcance limitado de cada rol y el cambio de rol al cerrar sesión.

### 7. Ejecutar las pruebas

Con el entorno virtual activo:

```powershell
python -m unittest discover -s tests -v
```

## Estructura actual

```text
UAB-GYM/
├── app/
│   ├── __init__.py       # Fábrica Flask-AppBuilder y comandos de aplicación
│   ├── security.py       # Permisos de los roles Recepcionista y Entrenador
│   ├── models.py         # Entidades del gimnasio y relaciones
│   ├── services.py       # Reglas de membresías, pagos y asistencias
│   ├── services_reportes.py # Consultas y agregaciones de reportes
│   ├── reportes_filtros.py  # Validación de filtros
│   ├── reportes_csv.py   # Exportación segura
│   ├── templates/reportes/ # Plantillas administrativas de reportes
│   └── views/
│       ├── __init__.py
│       ├── base.py       # Desactivación lógica compartida
│       ├── entrenadores.py
│       ├── planes.py
│       ├── socios.py     # Vistas CRUD, validaciones y desactivación lógica
│       ├── membresias.py
│       ├── pagos.py
│       ├── asistencias.py
│       └── reportes.py
├── tests/
│   ├── test_config.py    # Pruebas de configuración
│   ├── test_models.py    # Pruebas de tablas y restricciones
│   ├── test_entrenador_view.py
│   ├── test_plan_view.py
│   ├── test_security_roles.py # Pruebas de autorización por rol
│   ├── test_socio_view.py # Pruebas de configuración del CRUD de socios
│   ├── test_membresias.py
│   ├── test_pagos.py
│   ├── test_asistencias.py
│   ├── test_reporte_membresias.py
│   ├── test_reporte_pagos.py
│   ├── test_reporte_asistencias.py
│   ├── test_reportes_filtros_csv.py
│   └── test_reportes_security.py
├── .env.example          # Plantilla sin credenciales reales
├── .gitignore
├── config.py             # Configuración de secretos y conexión MySQL
├── README.md
└── requirements.txt
```

Los planes guardan su duración como cantidad de días (`duracion_dias`). Los estados aceptados por la base son `activo` e `inactivo`. En esta rama están disponibles los CRUD de socios, entrenadores, planes, membresías, pagos y asistencias, junto con los tres reportes administrativos descritos abajo. El rol Entrenador solo puede consultar planes hasta que exista una relación verificable de asignación; no tiene acceso a información personal, asistencias ni reportes.

## Flujo de trabajo Git

Desarrolla cada etapa en una rama `feature/...`, no directamente en `main`. Antes de guardar cambios, revisa:

```powershell
git status
git diff
```

Comprueba también que `.env` y otros archivos sensibles no aparezcan en el diff. Al terminar una etapa, crea un commit descriptivo y publica la rama:

```powershell
git add <archivos-revisados>
git commit -m "feat: <descripción breve en español>"
git push -u origin feature/<modulo>
```

Después crea un Pull Request hacia `develop` y espera la revisión antes de integrar los cambios. No se realizan commits automáticamente.

## Solución de errores frecuentes

- **`SECRET_KEY debe tener al menos 32 caracteres`:** genera una clave con el comando de Python de la sección de configuración y actualiza `.env`.
- **Error de conexión o acceso denegado:** confirma que MySQL está iniciado en XAMPP y que `DB_HOST`, `DB_PORT`, `DB_USER` y `DB_PASSWORD` coinciden con tu servidor.
- **No existe `uab_gym`:** créala en phpMyAdmin siguiendo la sección correspondiente.
- **No se encuentra el comando `flask`:** activa `.venv` e instala las dependencias con `python -m pip install -r requirements.txt`.
- **No se activa el entorno virtual:** utiliza el comando `Set-ExecutionPolicy -Scope Process ...` indicado arriba.
## Membresías, pagos y asistencias

Los módulos administrativos nuevos están disponibles bajo la categoría **Gimnasio**:

- **Membresías**: vincula un socio activo con un plan activo. El vencimiento se calcula de forma inclusiva según la duración del plan, se conserva el precio pactado y se rechazan períodos superpuestos. La cancelación y renovación conservan el historial.
- **Pagos**: registra pagos parciales con Efectivo, Transferencia bancaria, QR u Otro. El saldo se deriva de los pagos válidos y los pagos anulados se conservan junto con fecha y motivo de anulación.
- **Asistencias**: valida socio y membresía vigentes para registrar entradas, previene entradas abiertas duplicadas y permite registrar la salida posteriormente.

## Base de datos

El comando existente `flask init-db` crea las tablas nuevas `membresias`, `pagos` y `asistencias` cuando no existen. `db.create_all()` no actualiza tablas ya existentes; estas adiciones no requieren cambiar las tablas previas. Ejecuta los comandos de la aplicación con la misma configuración de entorno que el resto del proyecto:

```powershell
flask --app app:create_app init-db
flask --app app:create_app configure-roles
```

Recepcionista puede consultar y gestionar membresías, registrar pagos y operar entradas y salidas. No puede editar ni anular pagos ni corregir o anular asistencias. Entrenador no recibe acceso a datos personales o financieros. Admin conserva los permisos completos administrados por Flask-AppBuilder.

Las operaciones de membresías, pagos y asistencias se centralizan en `app/services.py` para que las vistas y las pruebas apliquen las mismas validaciones. Las fechas de asistencia se guardan como `DateTime` sin zona; el reloj de la aplicación las genera en `America/La_Paz`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

## Reportes administrativos

Desde el menú **Reportes** se accede a tres pantallas de consulta con indicadores, filtros, detalle paginado y descarga CSV. Las consultas usan exclusivamente registros existentes. No crean tablas ni actualizan contratos, pagos o asistencias.

| Pantalla | Ruta | Admin | Recepcionista | Entrenador |
|---|---|---|---|---|
| Reporte de membresías | `/reportes/membresias/` | Consultar y exportar | Consultar y exportar | Sin acceso |
| Reporte de ingresos y pagos | `/reportes/pagos/` | Consultar y exportar | Sin acceso | Sin acceso |
| Reporte de asistencias | `/reportes/asistencias/` | Consultar y exportar | Consultar y exportar | Sin acceso |

Cada vista utiliza el permiso `can_consultar` de su clase (`ReporteMembresiasView`, `ReportePagosView` o `ReporteAsistenciasView`) tanto para la pantalla como para `/exportar.csv`. Se exige sesión iniciada y autorización también al acceder mediante URL directa. Las rutas solo admiten consultas GET; los reportes no exponen operaciones de modificación. Los permisos anteriores de los CRUD se conservan. No se añaden permisos a Public ni se retiran permisos de Admin.

En el equipo que tenga el entorno preparado, sincroniza los permisos con el comando existente:

```powershell
flask --app app:create_app configure-roles
```

### Membresías

Muestra total de contratos, vigentes, vencidos, programados, cancelados y próximos a vencer. Las cuatro categorías de vigencia son excluyentes; las próximas a vencer son un subconjunto de las vigentes. El vencimiento es inclusivo y un contrato que vence en la fecha de consulta muestra 0 días restantes.

La clasificación reutiliza `Membresia.vigencia_en(fecha)` y su equivalente SQL `expresion_vigencia(fecha)`. La propiedad `vigencia` del CRUD delega en estos métodos conservando su comportamiento actual. No se almacenan estados temporales adicionales. La cancelación se interpreta según el estado administrativo actual, incluso al elegir una fecha de referencia pasada; el reporte no reconstruye versiones históricas de un contrato.

Filtros: nombre de socio (`socio`), ID de socio (`socio_id`), plan (`plan_id`), estado, fecha de referencia (`fecha_referencia`), inicio del contrato (`inicio_desde`/`inicio_hasta`) y vencimiento (`vencimiento_desde`/`vencimiento_hasta`). Los dos intervalos son independientes y ambos incluyen sus extremos. La ventana `dias_por_vencer` admite 0–365 días, con 7 por defecto; puede cambiarse por consulta o mediante la clave Flask `REPORTES_DIAS_POR_VENCER` antes de usar la vista.

El detalle contiene ID, nombre del socio, plan, inicio, vencimiento, precio pactado, estado y días restantes. El documento de identidad se excluye de pantallas y archivos porque no existe un permiso específico para divulgarlo en estos reportes; tampoco se consultan correo, teléfono ni dirección.

### Ingresos y pagos

Los ingresos son la suma decimal de pagos `valido`, incluidos los parciales por su importe efectivo. Se muestran la cantidad de pagos válidos, la cantidad de anulados y las distribuciones de ingresos por método y plan. La anulación excluye el importe de los ingresos, pero conserva la operación en el detalle. Cancelar una membresía no anula sus pagos históricos.

Filtros: `fecha_desde`/`fecha_hasta`, nombre o ID de socio, plan, `metodo_pago` y estado (`valido`/`anulado`). El período siempre se aplica a `fecha_pago`, también para contar anulados: no utiliza `fecha_anulacion`. Los métodos se obtienen de `METODOS_PAGO`, compartido con el CRUD.

**Alcance del saldo pendiente:** se calcula el saldo actual de todas las membresías que coinciden con los filtros de socio y plan, incluidas las que aún no tienen pagos y las canceladas. Para cada membresía se resta del precio pactado la suma de todos sus pagos válidos. Fechas, método y estado del pago no restringen este indicador. La pantalla muestra esta distinción y el número de membresías comprendidas. El saldo no se suma a los ingresos ni se recalcula usando el precio actual del plan. Se conserva la diferencia registrada, incluso si datos anteriores producen un saldo negativo; el reporte no corrige movimientos.

El detalle muestra ID del pago, fecha, socio, membresía, plan, monto, método, referencia y estado. Las uniones son a relaciones de uno a uno desde cada pago; los saldos utilizan una subconsulta agrupada por membresía para evitar duplicar el precio contratado.

### Asistencias

Muestra cantidad de asistencias efectivas, socios distintos, entradas abiertas, asistencias cerradas, frecuencia por socio y cantidad por día. Cada entrada cuenta una sola vez. Las anuladas se pueden inspeccionar en el detalle, pero se excluyen de indicadores y agrupaciones. El estado se obtiene del modelo existente.

Filtros: `fecha_desde`/`fecha_hasta`, nombre o ID de socio, `membresia_id` y estado (`abierta`/`cerrada`/`anulada`). El período se aplica a la fecha y hora de entrada, incluyendo todo el día final. La salida se presenta con fecha y hora para distinguir visitas que cruzan la medianoche.

### Fechas, precisión y paginación

- Los filtros diarios se interpretan en `America/La_Paz`, usando límites desde las 00:00 del día inicial hasta antes de las 00:00 del día siguiente al final. Se comparan directamente las columnas de fecha para aprovechar sus índices.
- El CRUD de pagos genera `fecha_pago` en UTC sin zona; el reporte convierte los límites locales a UTC y las horas mostradas a La Paz. Las agrupaciones financieras no cambian los importes ni convierten moneda.
- Las entradas creadas por el servicio y la vista de asistencia se guardan en hora local sin zona. Se mantienen tal como están para filtrar y agrupar días. **Limitación existente:** el valor predeterminado del modelo `Asistencia` usa UTC; registros creados directamente por ORM o importados podrían tener otra convención. Verifica la procedencia de los datos en el otro equipo antes de interpretar históricos. No se modifica ni migra ninguna fecha almacenada.
- Todos los importes se manejan con `Decimal`/`Numeric` y se presentan con dos decimales, sin separadores de miles ni símbolo de moneda añadido.
- El tamaño de página admite 10, 25, 50 o 100 filas. `pagina` controla el detalle y los resúmenes grandes tienen páginas independientes (`pagina_planes`, `pagina_socios`, `pagina_diaria`). Los enlaces conservan los filtros; los indicadores siempre consideran el conjunto completo.
- La búsqueda de nombres admite hasta 100 caracteres y trata `%` y `_` como texto literal. Se validan identificadores existentes, estados y métodos permitidos, fechas ISO entre 1900 y 9998, intervalos, paginación, claves desconocidas y parámetros repetidos.
- Un filtro incorrecto devuelve HTTP 400. Un resultado vacío muestra «No se encontraron registros para los filtros seleccionados». Un fallo técnico devuelve HTTP 500 con un mensaje genérico; los detalles quedan en el registro del servidor. Las respuestas usan `Cache-Control: private, no-store`.

### Exportaciones CSV

El botón **Exportar detalle CSV** descarga todos los registros autorizados que cumplen los filtros, independientemente de la página visible:

- `reporte_membresias.csv`
- `reporte_ingresos_pagos.csv`
- `reporte_asistencias.csv`

Se utilizan encabezados españoles, codificación `utf-8-sig` (BOM), separador `;`, fechas `AAAA-MM-DD`, horas de 24 horas e importes con punto decimal y dos posiciones. En Excel, si la configuración regional no reconoce el punto decimal, importa el archivo indicando ese separador decimal. Un conjunto vacío genera únicamente los encabezados.

Los textos que podrían interpretarse como fórmulas (`=`, `+`, `-`, `@`, tabulaciones o saltos de línea, incluso después de espacios) se prefijan con apóstrofo solo al exportarlos. Los datos originales no cambian. Las filas se recorren por lotes y el archivo se prepara en almacenamiento temporal, volcando a disco cuando supera 1 MiB; así no se cargan todos los registros en memoria y se detectan fallos antes de iniciar la descarga.

### Organización y pruebas pendientes

`app/services_reportes.py` reúne las selecciones, agregaciones y paginación SQL. `app/reportes_filtros.py` valida parámetros y `app/reportes_csv.py` formatea archivos. `app/views/reportes.py` define tres vistas de solo lectura, registradas por `appbuilder`; las plantillas de `app/templates/reportes/` reutilizan un diseño común. Esta organización sigue las [vistas protegidas BaseView de Flask-AppBuilder](https://flask-appbuilder.readthedocs.io/en/latest/views.html).

Se dejaron escritas pruebas en `test_reporte_membresias.py`, `test_reporte_pagos.py`, `test_reporte_asistencias.py`, `test_reportes_filtros_csv.py` y `test_reportes_security.py`. Cubren categorías y límites inclusivos, parciales y anulados, precisión, medianoche UTC/La Paz, agrupaciones, páginas y exportaciones completas, filtros inválidos, fórmulas CSV, privacidad, accesos por URL, errores y ausencia de escrituras. Los datos de ejemplo existen únicamente en fixtures SQLite en memoria.

**Validación local:** la suite completa se ejecutó con Python 3.13.5 y Flask-AppBuilder 5.3.0: 61 pruebas aprobadas sobre SQLite en memoria. Esto cubre el renderizado de las vistas y del tema, traducciones al español, permisos por sesión, consultas y exportaciones. La conexión y el comportamiento específico de MySQL/MariaDB se verificaron en MariaDB 10.11.16 local:

```powershell
python -m unittest discover -s tests -v
```

Queda verificar las consultas sobre MySQL/MariaDB (incluyendo agrupaciones y límites horarios) y la apertura de los CSV en Excel en el equipo de despliegue. Los reportes no requieren migraciones ni nuevas dependencias.

La inicialización de las vistas excluye las propiedades híbridas de los campos de búsqueda de Flask-AppBuilder, que solo admite columnas mapeadas en ese formulario. La validación de pagos nuevos considera `estado=None` como válido, igual que el valor predeterminado aplicado al insertar.
