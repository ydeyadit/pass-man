#!/usr/bin/env python3
# pip install cryptography

import argparse
import json
import os
import sys
import re
from getpass import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

# --- Constantes ---
CONFIG_DIR = os.path.expanduser("~/.pm")
MASTER_KEY_FILE = os.path.join(CONFIG_DIR, "master_key.json")
VAULT_FILE = os.path.join(CONFIG_DIR, "vault.json.enc")


# --- Utilidades ---
def create_config_dir():
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)


def validate_master_password(password: str) -> bool:
    if len(password) < 12:
        print("Error: mínimo 12 caracteres.")
        return False
    if not re.search(r"\d", password):
        print("Error: falta un número.")
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:'\"\\|,.<>/?`~]", password):
        print("Error: falta un símbolo.")
        return False
    if re.search(r"(.)\1", password):
        print("Error: no se permiten caracteres repetidos seguidos.")
        return False
    return True


def derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def generate_salt() -> bytes:
    return os.urandom(16)


def save_master_key_config(salt: bytes, hashed_key: bytes):
    config = {
        "salt": base64.b64encode(salt).decode(),
        "hashed_key": base64.b64encode(hashed_key).decode(),
    }
    with open(MASTER_KEY_FILE, "w") as f:
        json.dump(config, f)
    os.chmod(MASTER_KEY_FILE, 0o600)


def load_master_key_config() -> tuple[bytes, bytes] | None:
    if not os.path.exists(MASTER_KEY_FILE):
        return None
    with open(MASTER_KEY_FILE, "r") as f:
        config = json.load(f)
    return base64.b64decode(config["salt"]), base64.b64decode(config["hashed_key"])


def encrypt_vault(data: dict, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(json.dumps(data).encode())


def decrypt_vault(encrypted_data: bytes, key: bytes) -> dict:
    f = Fernet(key)
    try:
        return json.loads(f.decrypt(encrypted_data).decode())
    except Exception as e:
        print(f"Error al descifrar la bóveda: {e}")
        sys.exit(1)


def load_vault(master_password: str) -> dict:
    config = load_master_key_config()
    if not config:
        print("Error: falta master_key.json.")
        sys.exit(1)

    salt, stored_hashed_key = config
    user_hashed_key = derive_key(master_password, salt)

    if user_hashed_key != stored_hashed_key:
        print("Error: contraseña maestra incorrecta.")
        sys.exit(1)

    fernet_key = derive_key(master_password, salt)

    if not os.path.exists(VAULT_FILE):
        return {}

    with open(VAULT_FILE, "rb") as f:
        encrypted = f.read()

    return decrypt_vault(encrypted, fernet_key)


def save_vault(vault_data: dict, master_password: str):
    config = load_master_key_config()
    if not config:
        print("Error: falta master_key.json.")
        sys.exit(1)

    salt, _ = config
    fernet_key = derive_key(master_password, salt)

    encrypted = encrypt_vault(vault_data, fernet_key)
    with open(VAULT_FILE, "wb") as f:
        f.write(encrypted)
    os.chmod(VAULT_FILE, 0o600)


# --- NUEVA FUNCIÓN: CAMBIO DE CONTRASEÑA MAESTRA ---
def change_master_password(old_password: str):
    vault = load_vault(old_password)

    print("Cambiando la contraseña maestra...")
    while True:
        new_password = getpass("Nueva contraseña maestra: ")
        if validate_master_password(new_password):
            confirm = getpass("Confirma la nueva contraseña: ")
            if new_password == confirm:
                break
            else:
                print("Las contraseñas no coinciden.")
        else:
            print("La contraseña no cumple los requisitos.")

    new_salt = generate_salt()
    new_hashed_key = derive_key(new_password, new_salt)

    save_master_key_config(new_salt, new_hashed_key)

    encrypted = encrypt_vault(vault, new_hashed_key)
    with open(VAULT_FILE, "wb") as f:
        f.write(encrypted)
    os.chmod(VAULT_FILE, 0o600)

    print("Contraseña maestra cambiada exitosamente.")


# --- Setup inicial ---
def setup_master_password():
    print("Primera ejecución. Configura tu contraseña maestra.")
    while True:
        password = getpass("Nueva contraseña maestra: ")
        if validate_master_password(password):
            confirm = getpass("Confirma: ")
            if password == confirm:
                salt = generate_salt()
                hashed_key = derive_key(password, salt)
                save_master_key_config(salt, hashed_key)
                print("Contraseña maestra configurada.")
                return password
            else:
                print("No coinciden.")
        else:
            print("No válida.")


# --- Main ---
def main():
    create_config_dir()

    master_password = None
    if not os.path.exists(MASTER_KEY_FILE):
        master_password = setup_master_password()
        if not master_password:
            sys.exit(1)

    if not master_password:
        master_password = getpass("Contraseña maestra: ")

    parser = argparse.ArgumentParser(description="Gestor de contraseñas.")
    parser.add_argument("-t", "--todo", action="store_true")
    parser.add_argument("-c", "--cuenta")
    parser.add_argument("-u", "--usuario", action="store_true")
    parser.add_argument("-p", "--password", action="store_true")
    parser.add_argument("--add", action="store_true")
    parser.add_argument("--set-user")
    parser.add_argument("--set-pass")
    parser.add_argument("-d", "--delete", dest="delete_account")
    parser.add_argument(
        "--change-master", action="store_true", help="Cambiar la contraseña maestra."
    )

    args = parser.parse_args()

    # Nueva opción: cambiar contraseña maestra
    if args.change_master:
        change_master_password(master_password)
        sys.exit(0)

    vault = load_vault(master_password)

    if args.add:
        if not args.cuenta:
            print("Error: falta --cuenta.")
            sys.exit(1)

        account_name = args.cuenta
        username = args.set_user if args.set_user else input("Usuario: ")
        password = args.set_pass if args.set_pass else getpass("Contraseña: ")

        vault[account_name] = {"user": username, "password": password}
        save_vault(vault, master_password)
        print(f"Cuenta '{account_name}' guardada.")

    elif args.delete_account:
        account_name = args.delete_account
        if account_name not in vault:
            print("No existe.")
            sys.exit(1)
        confirm = input(f"Eliminar '{account_name}'? [s/N]: ")
        if confirm.lower() == "s":
            del vault[account_name]
            save_vault(vault, master_password)
            print("Eliminada.")
        else:
            print("Cancelado.")

    elif args.todo:
        if not vault:
            print("No hay cuentas.")
            return
        print("--- Cuentas ---")
        for name, data in vault.items():
            print(f"Nombre: {name}")
            print(f"  Usuario: {data['user'] or '(no especificado)'}")
            print("  Contraseña: *********")
        print("---------------")

    elif args.cuenta:
        account = args.cuenta
        if account not in vault:
            print("Cuenta inexistente.")
            sys.exit(1)
        if args.usuario:
            print("Usuario:", vault[account]["user"])
        elif args.password:
            print("Contraseña:", vault[account]["password"])
        else:
            print("Falta -u o -p.")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
