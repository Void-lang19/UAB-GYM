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

El comando crea `socios`, `entrenadores` y `planes` si todavía no existen; no elimina ni reinicia tablas. Flask-AppBuilder también administra sus tablas internas de seguridad. Las relaciones para membresías y los módulos del segundo integrante se incorporarán al acordar sus nombres y claves foráneas.

Verifica la conexión a `uab_gym`:

```powershell
flask --app app:create_app check-db
```

La respuesta correcta indica el nombre de la base y la versión de MySQL/MariaDB. Luego inicia el servidor local:

```powershell
flask --app app:create_app run --debug
```

Abre `http://127.0.0.1:5000` en el navegador. Detén el servidor con `Ctrl+C`.

En la primera inicialización, Flask-AppBuilder crea sus tablas internas de seguridad y permisos en `uab_gym`. Aún no se crea un usuario administrador.

## CRUD de socios

La sección **Gimnasio → Socios** permite registrar, buscar, consultar y editar socios. Se puede buscar por nombres, apellidos, documento, correo y estado. El documento es obligatorio; el correo, si se proporciona, debe tener formato válido; y la fecha de nacimiento no puede estar en el futuro.

El borrado físico está deshabilitado. Para conservar el historial que necesitarán las membresías, un usuario con permisos puede desactivar socios desde la acción de la tabla o cambiar su estado en el formulario. La pantalla requiere iniciar sesión; la creación de usuarios y la asignación de roles se documentarán en la etapa de autenticación.

### 7. Ejecutar las pruebas

Con el entorno virtual activo:

```powershell
python -m unittest discover -s tests -v
```

## Estructura actual

```text
UAB-GYM/
├── app/
│   ├── __init__.py       # Fábrica Flask-AppBuilder y comandos de base de datos
│   ├── models.py         # Esquema inicial de socios, entrenadores y planes
│   └── views/
│       ├── __init__.py
│       └── socios.py     # Vista CRUD, validaciones y desactivación lógica
├── tests/
│   ├── test_config.py    # Pruebas de configuración
│   ├── test_models.py    # Pruebas de tablas y restricciones
│   └── test_socio_view.py # Pruebas de configuración del CRUD de socios
├── .env.example          # Plantilla sin credenciales reales
├── .gitignore
├── config.py             # Configuración de secretos y conexión MySQL
├── README.md
└── requirements.txt
```

Los planes guardan su duración como cantidad de días (`duracion_dias`). Los estados aceptados por la base son `activo` e `inactivo`. El CRUD de socios ya está disponible; los CRUD de entrenadores y planes y la creación de usuarios administradores quedan para sus etapas.

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
