#!/usr/bin/env python3
# pip install cryptography

import argparse
import json
import os
import sys
import re
import time
import subprocess
import shutil
import threading
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
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")

SESSION_TTL = 300  # segundos
CLIPBOARD_CLEAR_TIME = 15  # segundos


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


# --- Clipboard ---
def is_wayland():
    return os.environ.get("WAYLAND_DISPLAY") is not None


def is_x11():
    return os.environ.get("DISPLAY") is not None


def copy_to_clipboard(text: str):
    try:
        if is_wayland() and shutil.which("wl-copy"):
            proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode())
            return True

        elif is_x11() and shutil.which("xclip"):
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode())
            return True

    except Exception:
        pass

    return False


def clear_clipboard(delay=CLIPBOARD_CLEAR_TIME):
    def _clear():
        time.sleep(delay)
        copy_to_clipboard("")

    threading.Thread(target=_clear, daemon=True).start()


# --- Sesión ---
def save_session(derived_key: bytes):
    data = {"key": base64.b64encode(derived_key).decode(), "time": time.time()}
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)
    os.chmod(SESSION_FILE, 0o600)


def load_session() -> bytes | None:
    if not os.path.exists(SESSION_FILE):
        return None

    with open(SESSION_FILE) as f:
        data = json.load(f)

    if time.time() - data["time"] > SESSION_TTL:
        os.remove(SESSION_FILE)
        return None

    return base64.b64decode(data["key"])


# --- Config ---
def save_master_key_config(salt: bytes, hashed_key: bytes):
    config = {
        "salt": base64.b64encode(salt).decode(),
        "hashed_key": base64.b64encode(hashed_key).decode(),
    }
    with open(MASTER_KEY_FILE, "w") as f:
        json.dump(config, f)
    os.chmod(MASTER_KEY_FILE, 0o600)


def load_master_key_config():
    if not os.path.exists(MASTER_KEY_FILE):
        return None
    with open(MASTER_KEY_FILE, "r") as f:
        config = json.load(f)
    return base64.b64decode(config["salt"]), base64.b64decode(config["hashed_key"])


# --- Vault ---
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


def load_vault(master_password: str | None) -> dict:
    config = load_master_key_config()
    if not config:
        print("Error: falta master_key.json.")
        sys.exit(1)

    salt, stored_hashed_key = config

    session_key = load_session()
    if session_key:
        fernet_key = session_key
    else:
        if not master_password:
            master_password = getpass("Contraseña maestra: ")

        user_hashed_key = derive_key(master_password, salt)

        if user_hashed_key != stored_hashed_key:
            print("Error: contraseña maestra incorrecta.")
            sys.exit(1)

        fernet_key = user_hashed_key
        save_session(fernet_key)

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


# --- Import JSON ---
def import_json(filepath: str, vault: dict) -> dict:
    with open(filepath) as f:
        data = json.load(f)

    count = 0

    if "items" in data:  # Bitwarden
        for item in data["items"]:
            name = item.get("name")
            login = item.get("login", {})
            username = login.get("username")
            password = login.get("password")

            if name and password:
                vault[name] = {"user": username, "password": password}
                count += 1

    elif isinstance(data, dict):  # genérico
        for name, entry in data.items():
            if isinstance(entry, dict):
                vault[name] = {
                    "user": entry.get("user"),
                    "password": entry.get("password"),
                }
                count += 1

    print(f"{count} cuentas importadas.")
    return vault


# --- Setup ---
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
                print("Configurada.")
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

    parser = argparse.ArgumentParser(description="Gestor de contraseñas.")
    parser.add_argument("-t", "--todo", action="store_true")
    parser.add_argument("-c", "--cuenta")
    parser.add_argument("-u", "--usuario", action="store_true")
    parser.add_argument("-p", "--password", action="store_true")
    parser.add_argument("--add", action="store_true")
    parser.add_argument("--set-user")
    parser.add_argument("--set-pass")
    parser.add_argument("-d", "--delete", dest="delete_account")
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--import-json")

    args = parser.parse_args()

    vault = load_vault(master_password)

    if args.import_json:
        vault = import_json(args.import_json, vault)
        save_vault(vault, master_password or getpass("Contraseña maestra: "))

    elif args.add:
        account_name = args.cuenta
        username = args.set_user if args.set_user else input("Usuario: ")
        password = args.set_pass if args.set_pass else getpass("Contraseña: ")

        vault[account_name] = {"user": username, "password": password}
        save_vault(vault, master_password or getpass("Contraseña maestra: "))
        print(f"Cuenta '{account_name}' guardada.")

    elif args.delete_account:
        account_name = args.delete_account
        if account_name in vault:
            del vault[account_name]
            save_vault(vault, master_password or getpass("Contraseña maestra: "))
            print("Eliminada.")

    elif args.todo:
        for name, data in vault.items():
            print(f"{name} -> {data['user']}")

    elif args.cuenta:
        account = args.cuenta
        if account not in vault:
            print("No existe.")
            sys.exit(1)

        if args.usuario:
            print(vault[account]["user"])

        elif args.password:
            pwd = vault[account]["password"]

            if args.copy:
                if copy_to_clipboard(pwd):
                    print("Copiado al clipboard (se borra en 15s).")
                    clear_clipboard()
                else:
                    print(pwd)
            else:
                print(pwd)


if __name__ == "__main__":
    main()
