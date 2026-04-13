% pm(1)

# NOMBRE

    pm.py - Password Manager. Guarda Cuentas->Usuario->Contraseña

# SINOPSIS

uso: **pm.py** [-h] [-t] [-c CUENTA] [-u] [-p] [--add] [--set-user SET_USER] [--set-pass SET_PASS] [-d DELETE_ACCOUNT] [--copy]
[--import-json IMPORT_JSON]

# DESCRIPCIÓN

pm es un password manager BÁSICO
Se encarga de crear, borrar y guardar una bóveda encriptada en la que sus elementos tienen la forma:
CUENTA->USUARIO->CONTRASEÑA (tercias)
Tal bóveda y llave se encuentran en ~/.pm/{vault.json.enc,master_key.json} junto con session.json
session.json se encarga de mantener 'abierta' la sesión durante 5 minutos(lo que se puede editar en el script pm.py) a fin de no tener que teclear una y otra vez la contraseña maestra.

# COMANDOS

    -h, --help
    -t, --todo
    -c, --cuenta CUENTA
    -u, --usuario
    -p, --password
    --add
    --set-user SET_USER
    --set-pass SET_PASS
    -d, --delete DELETE_ACCOUNT
    --copy
    --import-json IMPORT_JSON

# OPCIONES

    -h, --help Muestra la ayuda
    -t Muestra todo el contenido de la bóveda
    -c, --cuenta CUENTA Especifica la cuenta que se quiere consultar,borrar o crear
    -u, --usuario En combinación con -c indica al script que se quiere consultar su usuario
    -p, --password En combinación con -c indica al script que se quiere consultar su contraseña
    --add Añade cuenta a la bóveda. pm --add CUENTA. Pide USUARIO y CONTRASEÑA
    --set-user Establece USUARIO pm --add --cuenta CUENTA --set-user USUARIO --set-pass CONTRASEÑA
    --set-pass Establece CONTRASEÑA pm --add --cuenta CUENTA --set-user USUARIO --set-pass CONTRASEÑA
    -d, --delete Elimina la tercia CUENTA->USUARIO->CONTRASEÑA
    --copy copia salida al clipboard primario del sistema xclip (X11)o wl-copy (WAYLAND)
    --import-json Importa bóveda sin encriptar de otro servicio (como Bitwarden principalmente)

# EJEMPLOS

    pm -h Ayuda
    pm -t Toda la bóveda formateada: CUENTA -> USUARIO
    pm -c CUENTA -p Imprime la contraseña de CUENTA
    pm -c CUENTA -u Imprime el usuario de CUENTA
    pm --add CUENTA Crea tercia CUENTA -> USUARIO -> CONTRASEÑA de modo interactivo
    pm --add --cuenta CUENTA --set-user USUARIO --set-pass CONTRASEÑA Crea tercia
    pm -d CUENTA Elimina tercia
    pm -c CUENTA -p --copy Copia CONTRASEÑA de CUENTA. Esta opción solo sirve con -p
    pm --import-json JSON Importa bóveda de otro servicio en formato json en texto plano

# AUTOR

Creado con IA Nov/2025\
Revisado por t0no6al\
Mejorado al 100% por **toño**.
