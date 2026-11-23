"""
WIND 2.0 — Instalador / Setup inicial
Uso: python install.py

O que faz:
  1. Verifica Python >= 3.10
  2. Cria diretórios necessários (data/, backups/, logs/)
  3. Aplica migrações de banco (data/wind.db)
  4. Oferece configurar WIND_API_KEY (gera chave aleatória)
  5. Roda health check e exibe relatório de Release Candidate

Não destrói dados existentes. Seguro rodar mais de uma vez.
Nunca coloca chaves de API no código — usa variáveis de ambiente.
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def _header(msg: str) -> None:
    print(f"\n{'─'*55}")
    print(f"  {msg}")
    print(f"{'─'*55}")


def _step(msg: str) -> None:
    print(f"\n▶  {msg}")


def _ok(msg: str) -> None:
    print(f"   ✅  {msg}")


def _warn(msg: str) -> None:
    print(f"   ⚠️  {msg}")


def _fail(msg: str) -> None:
    print(f"   ❌  {msg}")


def check_python() -> bool:
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        _fail(f"Python {major}.{minor} — necessário >= 3.10")
        return False
    _ok(f"Python {major}.{minor}.{sys.version_info.micro}")
    return True


def create_directories() -> None:
    dirs = ["data", "backups", "logs", "spikes"]
    for d in dirs:
        path = ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        _ok(f"Diretório {d}/ — ok")


def run_migrations() -> None:
    sys.path.insert(0, str(ROOT))
    from src.installer.updater import Migrator
    migrator = Migrator(ROOT / "data" / "wind.db")
    status   = migrator.status()
    if status["up_to_date"]:
        _ok(f"Banco já está na versão {status['current_version']} — sem migrações pendentes")
        return
    applied = migrator.migrate()
    _ok(f"Migrações aplicadas: {applied} → versão {migrator.current_version()}")


def configure_wind_api_key() -> None:
    existing = os.getenv("WIND_API_KEY", "")
    if existing and len(existing) >= 16:
        _ok("WIND_API_KEY já configurada — mantendo")
        return
    _warn("WIND_API_KEY não configurada. Gerando chave aleatória...")
    key = secrets.token_urlsafe(32)
    print(f"\n   Chave gerada (guarde em local seguro):")
    print(f"   WIND_API_KEY = {key}")
    print(f"\n   Para configurar permanentemente no Windows:")
    print(f"   setx WIND_API_KEY \"{key}\"")
    print()
    # Escrita em .env.wind (nunca em código)
    env_file = ROOT / ".env.wind"
    if not env_file.exists():
        env_file.write_text(f"WIND_API_KEY={key}\n", encoding="utf-8")
        _ok(f".env.wind criado com a chave (não commitar este arquivo!)")
    else:
        _warn(".env.wind já existe — não sobrescrito")


def run_health_check() -> bool:
    from src.installer.health_check import HealthChecker
    checker = HealthChecker(ROOT)
    report  = checker.run()
    print()
    print(report.summary())
    return report.rc_ready()


def main() -> None:
    _header("WIND 2.0 — Instalador / Setup")

    _step("Verificando Python...")
    if not check_python():
        sys.exit(1)

    _step("Criando diretórios...")
    create_directories()

    _step("Inicializando banco de dados...")
    run_migrations()

    _step("Configurando WIND_API_KEY...")
    configure_wind_api_key()

    _step("Rodando health check...")
    rc_ok = run_health_check()

    _header("Instalação concluída")
    if rc_ok:
        print("  ✅  WIND pronta para uso. Inicie com:")
        print("       python src/wind.py")
    else:
        print("  ⚠️  Instalação com avisos. Veja acima e configure as")
        print("       variáveis de ambiente faltantes antes de usar.")
        print("       python src/wind.py funcionará com capacidades limitadas.")
    print()


if __name__ == "__main__":
    main()
