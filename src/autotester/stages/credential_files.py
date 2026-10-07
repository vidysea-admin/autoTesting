"""Which file names and suffixes hold credentials; they are refused without being opened."""

from pathlib import Path

_NAMES = {
    ".env", ".envrc", ".npmrc", ".netrc", ".pypirc", ".htpasswd",
    "credentials", "credentials.json", "credentials.yml", "credentials.md",
    "secrets.json", "secrets.yaml", "secrets.md", "service-account.json", "token.json",
    "id_rsa", "id_ed25519", "id_ecdsa",
}
_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".p8"}


def is_credential(path: Path) -> bool:
    name = path.name.lower()
    return name in _NAMES or name.startswith(".env.") or path.suffix.lower() in _SUFFIXES
