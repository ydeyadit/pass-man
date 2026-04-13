1. El Lanzador: pm (Script de Bash)

Este script es un "envoltorio" o "lanzador" diseñado para hacer más cómodo el uso del programa principal de Python. Su única función es ejecutar el script pm.py con el intérprete de Python correcto y pasarle todos los argumentos.

Análisis de su Funcionamiento:

- Propósito Principal: Evitar que tengas que activar manualmente el entorno virtual (venv) cada vez que quieras usar el gestor de contraseñas.
- Lógica Clave:
  1.  Obtener Ruta del Script:
      - Comando: SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" ... )"
      - Acción: Detecta la ruta absoluta del directorio donde se encuentra el propio script pm. Esto es crucial para que pueda localizar pm.py y el directorio venv/ sin importar desde qué directorio lo llames.
  2.  Definir Rutas:
      - `PYTHON_VENV`: Construye la ruta completa hacia el ejecutable de Python que está dentro del entorno virtual (pass-man/venv/bin/python).
      - `MAIN_SCRIPT`: Construye la ruta completa hacia el script principal (pass-man/pm.py).
  3.  Ejecutar y Transferir Control:
      - Comando: exec `"$PYTHON_VENV" "$MAIN_SCRIPT" "$@"`
      - Acción: Este es el núcleo del lanzador.
        - exec: Reemplaza el proceso actual (el script de Bash) por el comando de Python. Es una pequeña optimización.
        - `"$PYTHON_VENV" "$MAIN_SCRIPT"`: Llama al intérprete de Python del venv para que ejecute el script pm.py.
        - `"$@"`: Es una variable especial de Bash que se expande a todos los argumentos que le pasaste al script pm. Por ejemplo, si ejecutas:

        `pm --add --cuenta "Google"`

        el "$@" se convierte en `--add --cuenta "Google"`
        , pasándoselo directamente a pm.py.

---

2. La Lógica Principal: pm.py (Script de Python)

Este archivo contiene toda la lógica del gestor de contraseñas. Se encarga de la seguridad, el almacenamiento y la interacción con el usuario.

Análisis de su Arquitectura y Flujo:

A. Principios de Seguridad

- Contraseña Maestra:
  - Función: Es tu única llave para acceder a toda la bóveda.
  - Validación: La función `validate_master_password()` impone reglas de robustez (longitud, números, símbolos, etc.) para asegurar que sea una contraseña fuerte.
- Derivación de Clave (KDF - Key Derivation Function):
  - Problema que Resuelve: Nunca se debe usar una contraseña directamente para cifrar.
  - Solución: Se usa PBKDF2HMAC para convertir tu contraseña maestra en una clave criptográfica segura.
    - Función Clave: `derive_key()`
    - `Salt` (Sal): Un valor aleatorio único `(os.urandom(16))` que se combina con tu contraseña. Evita que dos usuarios con la misma contraseña tengan la
      misma clave de cifrado. Se guarda en master_key.json.
    - Iteraciones: El proceso se repite 480,000 veces. Esto hace que un atacante que intente adivinar tu contraseña por fuerza bruta necesite una cantidad de tiempo y recursos computacionales enorme.
- Cifrado de la Bóveda:
  - Algoritmo: Utiliza Fernet de la librería cryptography.
  - Característica: Proporciona "cifrado autenticado", lo que significa que no solo cifra los datos, sino que también firma el contenido cifrado para
    asegurar que no ha sido modificado o corrupto.
  - Funciones Clave: `encrypt_vault()` y `decrypt_vault()`.

B. Estructura de Almacenamiento

Todos los archivos se guardan en un directorio oculto en tu home: ~/.pm/.

- `master_key.json`:
  - Contenido: NO contiene tu contraseña maestra. Almacena la salt y un hash de la clave derivada.
  - Mecanismo de Verificación: Cuando introduces tu contraseña, el script la combina con la salt guardada, realiza las 480,000 iteraciones y compara el resultado con el hash almacenado. Si coinciden, la contraseña es correcta. Esto permite verificarla sin guardarla en ningún sitio.
- `vault.json.enc`:
  - Contenido: Este es el archivo de tu bóveda. Es un fichero binario que contiene todas tus cuentas ({nombre_cuenta: {user: '...', pass: '...'}}) en formato JSON, pero completamente cifrado con la clave derivada. Sin la clave, es indescifrable.

C. Flujo de Ejecución del Programa

1.  Inicio (`main()`): Llama a create_config_dir() para asegurar que ~/.pm exista y tenga los permisos correctos (rwx------), de modo que solo tú puedas acceder.

2.  Primera Ejecución (`setup_master_password()`):
    - Si master_key.json no existe, el script asume que es el primer uso.
    - Te guía para crear y validar una contraseña maestra.
    - Genera la salt, deriva la clave, la "hashea" y guarda la salt y el hash en master_key.json.

3.  Ejecución Normal (Desbloqueo):
    - Pide la contraseña maestra (getpass la oculta mientras escribes).
    - Llama a load_vault(), que realiza el proceso de verificación explicado en el punto B. Si la contraseña es incorrecta, el programa se detiene.

4.  Operación (Tras el Desbloqueo):
    - Con la bóveda descifrada en memoria, usa el módulo argparse para leer los argumentos de la línea de comandos (--add, -c, -p, etc.).
    - Ejecuta la acción solicitada (añadir, listar, mostrar usuario/contraseña).

5.  Guardado Final (`save_vault()`):
    - Si realizaste algún cambio (como añadir una cuenta con --add), la función save_vault() vuelve a tomar el diccionario completo de la bóveda en memoria, lo cifra de nuevo con tu clave y sobrescribe el archivo vault.json.enc.

Añadir una función de eliminación es un paso crucial para que el gestor sea completo.

Para implementar esta funcionalidad de forma segura y coherente con el diseño actual, se necesita modificar el script principal pm.py. El plan se divide en dos pasos principales:

1.  Definir un Nuevo Argumento: Crearemos un nuevo argumento en la línea de comandos (por ejemplo, -d o --delete) para que el usuario pueda especificar qué cuenta desea eliminar.
2.  Implementar la Lógica de Eliminación: Añadiremos un bloque de código que se ejecute cuando se use el nuevo argumento. Este bloque se encargará de buscar la cuenta, pedir confirmación al usuario, eliminarla y guardar la bóveda actualizada.

# Resumen del Uso para el Usuario

1. # El usuario decide eliminar su cuenta de "Amazon"
2. pm --delete Amazon

La terminal le pedirá su contraseña maestra y luego la confirmación:

1. Contraseña maestra para desbloquear pm: **\*\*\*\***
2. ¿Estás seguro de que quieres eliminar la cuenta 'Amazon'? Esta acción no se puede deshacer. [s/N]: s
3. La cuenta 'Amazon' ha sido eliminada exitosamente.

Este enfoque es seguro, pide confirmación y se integra limpiamente con la estructura existente del programa.

master_key.json contiene datos (la sal y el hash de verificación) en un formato
legible.
Lejos de ser un descuido, este diseño es intencional y sigue el modelo de seguridad estándar de la industria para este tipo de aplicaciones.

# El Rol de master_key.json y el Secreto Real

Si un atacante obtiene tanto vault.json.enc como master_key.json, tiene casi todo lo necesario para intentar descifrar tu bóveda.

- Lo que el atacante OBTIENE:
  1.  La bóveda cifrada (`vault.json.enc`): El cofre del tesoro, completamente cerrado.
  2.  La sal (`salt` de `master_key.json`): Un ingrediente público necesario para la receta de la clave.
  3.  El hash de verificación (`hashed_key` de `master_key.json`): El "candado" que les dice si su intento de llave fue exitoso.

- Lo que al atacante le FALTA (El Verdadero Secreto):
  - Tu Contraseña Maestra.

La seguridad de todo el sistema no depende de ocultar la sal o el hash, sino de hacer que el proceso de adivinar la contraseña maestra sea computacionalmente inviable.

# El Flujo de Ataque y las Defensas del Sistema

Imaginemos que un atacante tiene esos dos archivos. Para poder abrir tu bóveda, debe ejecutar un "ataque de fuerza bruta offline". Este es el proceso que tendría que seguir:

1.  Elige una contraseña para probar (ej: password123).
2.  Toma la salt de tu master_key.json.
3.  Combina su intento (password123) con tu salt.
4.  Pasa esa combinación a través de la Función de Derivación de Clave (PBKDF2) con 480,000 iteraciones.
5.  Compara el resultado con la hashed_key guardada en tu master_key.json.

Si no coinciden (que es lo más probable), debe repetir el proceso desde el paso 1 con una nueva contraseña (password124, 12345678, etc.).

No es una debilidad grave; es el modelo de seguridad aceptado. La protección se traslada de la "seguridad por oscuridad" (esconder la sal o el hash) a la "seguridad por costo computacional", que depende directamente de la fortaleza de la contraseña maestra del usuario.

# Una misma bóveda en dos máquinas

Para tener la bóveda funcionando en ambas máquinas, necesitaras sincronizar:

1. El Directorio de Configuración del Gestor (~/.pm/)

- Contenido: Este directorio contiene el corazón de tu bóveda:
  - master_key.json: Tu "llave maestra" (sal y hash de verificación de la contraseña maestra).
  - vault.json.enc: Tu bóveda de contraseñas cifrada.
- Importancia: Absolutamente esencial. Sin estos archivos, el gestor no puede funcionar en ninguna máquina, ya que no sabría dónde guardar ni qué descifrar, ni cómo verificar tu contraseña maestra.

2. El Directorio del Proyecto (pass-man/)

- Contenido:
  - pm.py: El código principal del gestor de contraseñas.
  - pm: El lanzador de Bash para ejecutar pm.py.
  - venv/: El entorno virtual de Python o crear uno nuevo en la otra máquina.
- Importancia de `pm.py` y `pm`: deben estar sincronizados para asegurar la misma lógica y el mismo punto de entrada en ambas máquinas.
- Importancia y Consideraciones del `venv/`:
  - Necesidad del `venv`: El lanzador pm está configurado para usar específicamente el intérprete de Python dentro del directorio del entorno virtual (venv/)
  - Problema de Portabilidad: Generalmente, los entornos virtuales de Python no son directamente portables entre diferentes sistemas operativos o incluso entre versiones significativamente distintas de Python en el misma OS. Contienen binarios y rutas específicas del sistema donde fueron creados. Simplemente copiar la carpeta venv/ de una máquina a otra podría causar errores. Por lo tanto, en lugar de sincronizar venv/ directamente, la práctica estándar sería:
    1.  Excluir `venv/` de la sincronización (por ejemplo, añadiéndolo a un .gitignore).
    2.  Recrear el entorno virtual en la segunda máquina.
    3.  Instalar las dependencias necesarias en ese nuevo venv.

# Pasos Detallados para la Segunda Máquina (Asumiendo que pass-man/ está sincronizado, pero sin `venv/`):

1.  Sincronizar el directorio `~/.pm/` completamente.
2.  Sincronizar el directorio `pass-man/` (asegurándote de que venv/ no se copia, o se ignora).
3.  Navegar al directorio `pass-man/` en la segunda máquina:

`cd /ruta/a/tu/proyecto/pass-man/`

4.  Crear el entorno virtual (con venv como ejemplo):
    `python3 -m venv venv`

5.  Instalar las dependencias: El único módulo de terceros que usa pm.py es cryptography.

`./venv/bin/pip install cryptography`

(Idealmente, para proyectos más complejos, tendrías un archivo requirements.txt con todas las dependencias listadas, que instalarías con pip install -r requirements.txt. Pero esto es un proyecto super amateur con más fallas que líneas de código)(Y SIN EMBARGO FUNCIONA 🤓).

Una vez completados estos pasos, el lanzador pm y la bóveda deberían funcionar sin problemas en la segunda máquina, aprovechando un entorno Python configurado correctamente para esa instancia.

## ✨ Funcionalidades Avanzadas (v2.0)

Esta versión del gestor (`pm-con-timeout-importarbwjson.py`) incluye mejoras críticas de usabilidad y seguridad:

### 🕒 Sesión Persistente (Timeout)

Implementa un sistema de "sesión abierta" de **5 minutos** (modificable en la línea correspondiente).
Al desbloquear la bóveda por primera vez, se genera un token temporal en `~/.pm/session.json`. Esto permite ejecutar múltiples comandos sin reintroducir la contraseña maestra constantemente.

### 📥 Importación Masiva

Soporte para importar bases de datos externas mediante archivos JSON:

- **Bitwarden:** Importación directa de exportaciones estándar.
- **Genérico:** Estructura flexible de `cuenta: {user, password}`.
  _Uso:_ `pm --import-json backup.json`

### 📋 Portapapeles Seguro

Integración con `wl-copy` (Wayland) y `xclip` (X11).

- Al usar `--copy`, la contraseña se envía al portapapeles.
- **Auto-destrucción:** Un proceso en segundo plano limpia el portapapeles tras **15 segundos** para evitar fugas de información.()
