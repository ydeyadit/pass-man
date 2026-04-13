1. El Lanzador: pm (Script de Bash)

Este script es un "envoltorio" o "lanzador" diseñado para hacer más cómodo el
uso del programa principal de Python. Su única función es ejecutar el script
pm.py con el intérprete de Python correcto y pasarle todos los argumentos.

Análisis de su Funcionamiento:

- Propósito Principal: Evitar que tengas que activar manualmente el entorno
  virtual (venv) cada vez que quieras usar el gestor de contraseñas.
- Lógica Clave:
  1.  Obtener Ruta del Script:
      - Comando: SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" ... )"
      - Acción: Detecta la ruta absoluta del directorio donde se encuentra el
        propio script pm. Esto es crucial para que pueda localizar pm.py y el
        venv sin importar desde qué directorio lo llames.
  2.  Definir Rutas:
      - `PYTHON_VENV`: Construye la ruta completa hacia el ejecutable de Python
        que está dentro del entorno virtual (pass-man/venv/bin/python).
      - `MAIN_SCRIPT`: Construye la ruta completa hacia el script principal
        (pass-man/pm.py).
  3.  Ejecutar y Transferir Control:
      - Comando: exec "$PYTHON_VENV" "$MAIN_SCRIPT" "$@"
      - Acción: Este es el núcleo del lanzador.
        - exec: Reemplaza el proceso actual (el script de Bash) por el comando
          de Python. Es una pequeña optimización.
        - "$PYTHON_VENV" "$MAIN_SCRIPT": Llama al intérprete de Python del venv
          para que ejecute el script pm.py.
        - "$@": Es una variable especial de Bash que se expande a todos los argumentos que le pasaste al script pm.
                 Por ejemplo, si ejecutas pm --add --cuenta "Google", el "$@"
          se convierte en --add --cuenta "Google", pasándoselo directamente a
          pm.py.

---

2. La Lógica Principal: pm.py (Script de Python)

Este archivo contiene toda la lógica del gestor de contraseñas. Se encarga de la
seguridad, el almacenamiento y la interacción con el usuario.

Análisis de su Arquitectura y Flujo:

A. Principios de Seguridad

- Contraseña Maestra:
  - Función: Es tu única llave para acceder a toda la bóveda.
  - Validación: La función validate_master_password() impone reglas de robustez
    (longitud, números, símbolos, etc.) para asegurar que sea una contraseña
    fuerte.
- Derivación de Clave (KDF - Key Derivation Function):
  - Problema que Resuelve: Nunca se debe usar una contraseña directamente para
    cifrar.
  - Solución: Se usa PBKDF2HMAC para convertir tu contraseña maestra en una
    clave criptográfica segura.
    - Función Clave: derive_key()
    - `Salt` (Sal): Un valor aleatorio único (os.urandom(16)) que se combina con
      tu contraseña. Evita que dos usuarios con la misma contraseña tengan la
      misma clave de cifrado. Se guarda en master_key.json.
    - Iteraciones: El proceso se repite 480,000 veces. Esto hace que un atacante
      que intente adivinar tu contraseña por fuerza bruta necesite una cantidad
      de tiempo y recursos computacionales enorme.
- Cifrado de la Bóveda:
  - Algoritmo: Utiliza Fernet de la librería cryptography.
  - Característica: Proporciona "cifrado autenticado", lo que significa que no
    solo cifra los datos, sino que también firma el contenido cifrado para
    asegurar que no ha sido modificado o corrupto.
  - Funciones Clave: encrypt_vault() y decrypt_vault().

B. Estructura de Almacenamiento

Todos los archivos se guardan en un directorio oculto en tu home: ~/.pm/.

- `master_key.json`:
  - Contenido: NO contiene tu contraseña maestra. Almacena la salt y un hash de
    la clave derivada.
  - Mecanismo de Verificación: Cuando introduces tu contraseña, el script la
    combina con la salt guardada, realiza las 480,000 iteraciones y compara el
    resultado con el hash almacenado. Si coinciden, la contraseña es correcta.
    Esto permite verificarla sin guardarla en ningún sitio.
- `vault.json.enc`:
  - Contenido: Este es el archivo de tu bóveda. Es un fichero binario que
    contiene todas tus cuentas ({nombre_cuenta: {user: '...', pass: '...'}}) en
    formato JSON, pero completamente cifrado con la clave derivada. Sin la
    clave, es indescifrable.

C. Flujo de Ejecución del Programa

1.  Inicio (`main()`): Llama a create_config_dir() para asegurar que ~/.pm
    exista y tenga los permisos correctos (rwx------), de modo que solo tú
    puedas acceder.

2.  Primera Ejecución (`setup_master_password()`):
    - Si master_key.json no existe, el script asume que es el primer uso.
    - Te guía para crear y validar una contraseña maestra.
    - Genera la salt, deriva la clave, la "hashea" y guarda la salt y el hash en
      master_key.json.

3.  Ejecución Normal (Desbloqueo):
    - Pide la contraseña maestra (getpass la oculta mientras escribes).
    - Llama a load_vault(), que realiza el proceso de verificación explicado en
      el punto B. Si la contraseña es incorrecta, el programa se detiene.

4.  Operación (Tras el Desbloqueo):
    - Con la bóveda descifrada en memoria, usa el módulo argparse para leer los
      argumentos de la línea de comandos (--add, -c, -p, etc.).
    - Ejecuta la acción solicitada (añadir, listar, mostrar usuario/contraseña).

5.  Guardado Final (`save_vault()`):
    - Si realizaste algún cambio (como añadir una cuenta con --add), la función
      save_vault() vuelve a tomar el diccionario completo de la bóveda en
      memoria, lo cifra de nuevo con tu clave y sobrescribe el archivo
      vault.json.enc.

Añadir una función de eliminación es un paso crucial para que el gestor sea
completo.

Para implementar esta funcionalidad de forma segura y coherente con el diseño
actual, necesitamos modificar el script principal pm.py. El plan se divide en
dos pasos principales:

1.  Definir un Nuevo Argumento: Crearemos un nuevo argumento en la línea de
    comandos (por ejemplo, -d o --delete) para que el usuario pueda especificar
    qué cuenta desea eliminar.
2.  Implementar la Lógica de Eliminación: Añadiremos un bloque de código que se
    ejecute cuando se use el nuevo argumento. Este bloque se encargará de buscar
    la cuenta, pedir confirmación al usuario, eliminarla y guardar la bóveda
    actualizada.

A continuación, te presento el plan detallado con los fragmentos de código
exactos y su explicación.

Plan de Implementación para la Eliminación

Paso 1: Añadir el Argumento de Línea de Comandos

Necesitamos que el script entienda una nueva instrucción. Hacemos esto en la
sección donde se definen todos los argumentos con argparse.

- Archivo a Modificar: pass-man/pm.py
- Acción: Añadir la siguiente línea junto a las otras definiciones de
  parser.add_argument(...):

1 # ... (justo después de la definición de --set-pass) 2
parser.add_argument("-d", "--delete", dest="delete_account", help="Elimina una
cuenta especificada por su nombre."

- Explicación:
  - "-d", "--delete": Crea un argumento corto (-d) y uno largo (--delete).
  - dest="delete_account": Guarda el valor (el nombre de la cuenta a eliminar)
    en una variable llamada delete_account dentro del objeto args.
  - help="...": Proporciona el texto de ayuda que se mostrará si el usuario
    ejecuta pm --help.

Paso 2: Implementar la Lógica de Eliminación

Ahora, añadimos la lógica que se ejecutará cuando se llame al script con el
argumento --delete. El mejor lugar para este código es dentro de la función
main, junto a los otros bloques if/elif que manejan las acciones (--add, --todo,
etc.).

- Archivo a Modificar: pass-man/pm.py
- Acción: Insertar el siguiente bloque de código. Un buen lugar es justo después
  del bloque if args.add: y antes de elif args.todo:.

  1 # ... 2 # Cargar la bóveda 3 vault = load_vault(master_password) 4 5 if
  args.add: 6 # ... (lógica de añadir existente) 7 8 # --- INICIO DEL NUEVO
  BLOQUE DE CÓDIGO --- 9 elif args.delete_account:

10 account_name = args.delete_account 11 if account_name not in vault: 12
print(f"Error: La cuenta '{account_name}' no existe.") 13 sys.exit(1) 14 15 #
Pedir confirmación para seguridad 16 confirm = input(f"¿Estás seguro de que
quieres eliminar la cuenta '{account_name}'? Esta acción no se puede deshacer.
[s/N]: ") 17 if confirm.lower() == 's': 18 # Eliminar la cuenta del diccionario
19 del vault[account_name] 20 # Guardar la bóveda actualizada (y cifrada) 21
save_vault(vault, master_password) 22 print(f"La cuenta '{account_name}' ha sido
eliminada exitosamente.") 23 else: 24 print("Operación de eliminación
cancelada.") 25 # --- FIN DEL NUEVO BLOQUE DE CÓDIGO --- 26 27 elif args.todo:
28 # ... (lógica de listar existente) 29 # ...

- Explicación del Flujo:
  1.  `elif args.delete_account:`: El código solo se ejecuta si se usó el
      argumento --delete.
  2.  Verificación: Primero, comprueba si la cuenta que se quiere borrar
      (account_name) realmente existe en la bóveda (if account_name not in
      vault). Si no existe, informa al usuario y termina.
  3.  Confirmación del Usuario: Para evitar borrados accidentales, se usa
      input() para pedir una confirmación explícita. La operación solo continúa
      si el usuario escribe s o S.
  4.  Eliminación: del vault[account_name] elimina la entrada del diccionario
      que está en la memoria.
  5.  Guardado Permanente: save_vault(vault, master_password) toma el
      diccionario modificado, lo cifra por completo y lo guarda en
      vault.json.enc, sobrescribiendo la versión anterior. Este es el paso que
      hace el borrado permanente.

Resumen del Uso para el Usuario

Una vez implementados estos cambios, el flujo de uso sería muy sencillo:

1 # El usuario decide eliminar su cuenta de "Amazon" 2 pm --delete Amazon

La terminal le pedirá su contraseña maestra y luego la confirmación:

1 Contraseña maestra para desbloquear pm: **\*\*\*\*** 2 ¿Estás seguro de que
quieres eliminar la cuenta 'Amazon'? Esta acción no se puede deshacer. [s/N]: s
3 La cuenta 'Amazon' ha sido eliminada exitosamente.

Este enfoque es seguro, pide confirmación y se integra limpiamente con la
estructura existente del programa.

master_key.json contiene datos (la sal y el hash de verificación) en un formato
legible. Lejos de ser un descuido, este diseño es intencional y sigue el modelo
de seguridad estándar de la industria para este tipo de aplicaciones.

Vamos a analizar por qué no se considera una debilidad grave y dónde reside la
verdadera fortaleza del sistema.

El Rol de master_key.json y el Secreto Real

Tu observación es correcta: si un atacante obtiene tanto vault.json.enc como
master_key.json, tiene casi todo lo necesario para intentar descifrar tu bóveda.

- Lo que el atacante OBTIENE:
  1.  La bóveda cifrada (`vault.json.enc`): El cofre del tesoro, completamente
      cerrado.
  2.  La sal (`salt` de `master_key.json`): Un ingrediente público necesario
      para la receta de la clave.
  3.  El hash de verificación (`hashed_key` de `master_key.json`): El "candado"
      que les dice si su intento de llave fue exitoso.

- Lo que al atacante le FALTA (El Verdadero Secreto):
  - Tu Contraseña Maestra.

La seguridad de todo el sistema no depende de ocultar la sal o el hash, sino de
hacer que el proceso de adivinar la contraseña maestra sea computacionalmente
inviable.

El Flujo de Ataque y las Defensas del Sistema

Imaginemos que un atacante tiene esos dos archivos. Para poder abrir tu bóveda,
debe ejecutar un "ataque de fuerza bruta offline". Este es el proceso que
tendría que seguir:

1.  Elige una contraseña para probar (ej: password123).
2.  Toma la salt de tu master_key.json.
3.  Combina su intento (password123) con tu salt.
4.  Pasa esa combinación a través de la Función de Derivación de Clave (PBKDF2)
    con 480,000 iteraciones.
5.  Compara el resultado con la hashed_key guardada en tu master_key.json.

Si no coinciden (que es lo más probable), debe repetir el proceso desde el paso
1 con una nueva contraseña (password124, 12345678, etc.).

Aquí es donde entran las defensas clave:

┌──────────┬──────────────────────────────────────────────────┬──────────────────────────────────────────────────────────
───┐ │ Defensa │ Descripción │ ¿Por qué es efectiva? │
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────────────
───┤ │ **1. KD... │ La función derive_key está diseñada para ser ... │ Un
atacante no puede probar miles de millones de contras... │ │ **2. La... │ Es un
valor aleatorio único para tu bóveda. A... │ La salt inutiliza los "ataques de
tabla arcoíris" (rainb... │ │ \*\*3. La... │ Esta es la defensa más importante y
la que es... │ Si tu contraseña es larga, compleja y no predecible (com... │
└──────────┴──────────────────────────────────────────────────┴──────────────────────────────────────────────────────────
───┘

Una Analogía: La Caja Fuerte de un Banco

Piénsalo de esta manera:

- `vault.json.enc`: Es la puerta de acero de la bóveda del banco.
- `master_key.json`: Es el manual de especificaciones de la cerradura de la
  bóveda. El ladrón puede leer el manual, saber que es una cerradura de
  combinación con 10 diales y 100 números por dial, y entender perfectamente su
  mecanismo.
- Tu Contraseña Maestra: Es la combinación secreta de la cerradura.

Aunque el ladrón sepa todo sobre la cerradura (el hash y la salt), todavía tiene
que sentarse frente a la puerta y probar manualmente cada una de las 100^10
combinaciones posibles. El mecanismo de la cerradura (el KDF) hace que cada
intento tome un minuto, en lugar de un milisegundo.

Conclusión:

No es una debilidad grave; es el modelo de seguridad aceptado. La protección se
traslada de la "seguridad por oscuridad" (esconder la sal o el hash) a la
"seguridad por costo computacional", que depende directamente de la fortaleza de
la contraseña maestra del usuario.

Por eso, los gestores de contraseñas profesionales como Bitwarden o 1Password
funcionan bajo este mismo principio fundamental y ponen tanto énfasis en que
elijas una contraseña maestra robusta.

Para tener la bóveda funcionando en ambas máquinas, necesitarías sincronizar:

1. El Directorio de Configuración del Gestor (~/.pm/)

- Contenido: Este directorio contiene el corazón de tu bóveda:
  - master_key.json: Tu "llave maestra" (sal y hash de verificación de la
    contraseña maestra).
  - vault.json.enc: Tu bóveda de contraseñas cifrada.
- Importancia: Absolutamente esencial. Sin estos archivos, el gestor no puede
  funcionar en ninguna máquina, ya que no sabría dónde guardar ni qué descifrar,
  ni cómo verificar tu contraseña maestra.
- Sincronización: Sí, este directorio debe sincronizarse completamente y de
  forma idéntica entre las máquinas.

2. El Directorio del Proyecto (pass-man/)

- Contenido:
  - pm.py: El código principal del gestor de contraseñas.
  - pm: El lanzador de Bash para ejecutar pm.py.
  - venv/: El entorno virtual de Python.
- Importancia de `pm.py` y `pm`: Sí, son necesarios y deben estar sincronizados
  para asegurar la misma lógica y el mismo punto de entrada en ambas máquinas.
- Importancia y Consideraciones del `venv/`:
  - Necesidad del `venv`: El lanzador pm está configurado para usar
    específicamente el intérprete de Python dentro de pass-man/venv/bin/python.
    Por lo tanto, el entorno virtual es necesario para que el lanzador funcione
    como se espera.
  - Problema de Portabilidad: Generalmente, los entornos virtuales de Python no
    son directamente portables entre diferentes sistemas operativos o incluso
    entre versiones significativamente distintas de Python en la misma OS.
    Contienen binarios y rutas específicas del sistema donde fueron creados.
    Simplemente copiar la carpeta venv/ de una máquina a otra podría causar
    errores.
  - Solución Recomendada: En lugar de sincronizar venv/ directamente, la
    práctica estándar es:
    1.  Excluir `venv/` de la sincronización (por ejemplo, añadiéndolo a un
        .gitignore si estuviera en un repositorio de Git).
    2.  Recrear el entorno virtual en la segunda máquina.
    3.  Instalar las dependencias necesarias en ese nuevo venv.

Pasos Detallados para la Segunda Máquina (Asumiendo que pass-man/ está
sincronizado, pero sin `venv/`):

1.  Sincronizar el directorio `~/.pm/` completamente.
2.  Sincronizar el directorio `pass-man/` (asegurándote de que venv/ no se
    copia, o se ignora).
3.  Navegar al directorio `pass-man/` en la segunda máquina: 1 cd
    /ruta/a/tu/proyecto/pass-man/
4.  Crear el entorno virtual: 1 python3 -m venv venv
5.  Instalar las dependencias: El único módulo de terceros que usa pm.py es
    cryptography. 1 ./venv/bin/pip install cryptography (Idealmente, para
    proyectos más complejos, tendrías un archivo requirements.txt con todas las
    dependencias listadas, que instalarías con pip install -r requirements.txt).

Una vez completados estos pasos, el lanzador pm y la bóveda deberían funcionar
sin problemas en la segunda máquina, aprovechando un entorno Python configurado
correctamente para esa instancia.
