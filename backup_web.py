#!/usr/bin/env python3
"""
backup_web.py - Automação de backup e retenção do servidor web (Fedora/RHEL).

Etapas (em ordem):
  1. Garante a existência de /backup/web/
  2. Gera backup_web_AAAA-MM-DD_HH-MM.tar.gz com o conteúdo de /var/www/html/
  3. [EXTRA] Gera o hash SHA-256 e salva em <arquivo>.tar.gz.sha256
  4. Remove backups com mais de 7 dias (retenção)
  5. [EXTRA] Ajusta permissões: 700 nos diretórios e 600 nos arquivos de /backup/

Uso: sudo python3 backup_web.py
"""

import hashlib
import os
import sys
import tarfile
import time
from datetime import datetime

# ----------------------------- Configurações ------------------------------
ORIGEM = "/var/www/html/"
RAIZ_BACKUP = "/backup"
DESTINO = "/backup/web"
DIAS_RETENCAO = 7
# --------------------------------------------------------------------------


def verificar_root():
    """O script exige privilégios de superusuário (root ou sudo)."""
    if os.geteuid() != 0:
        print("[ERRO] Execute como root: sudo python3 backup_web.py")
        sys.exit(1)


def criar_diretorio():
    """Etapa 1 - Cria /backup/web/ se não existir."""
    if os.path.isdir(DESTINO):
        print(f"[OK] Diretório já existe: {DESTINO}")
    else:
        os.makedirs(DESTINO)
        print(f"[OK] Diretório criado: {DESTINO}")


def gerar_backup():
    """Etapa 2 - Cria o .tar.gz com o conteúdo de /var/www/html/."""
    if not os.path.isdir(ORIGEM):
        print(f"[ERRO] Diretório de origem não encontrado: {ORIGEM}")
        sys.exit(1)

    agora = datetime.now()
    nome = "backup_web_" + agora.strftime("%Y-%m-%d_%H-%M") + ".tar.gz"
    caminho = os.path.join(DESTINO, nome)

    print(f"[..] Compactando {ORIGEM} ...")
    with tarfile.open(caminho, "w:gz") as tar:
        # arcname="html" mantém uma pasta raiz dentro do pacote
        tar.add(ORIGEM, arcname="html")
    print(f"[OK] Backup gerado: {caminho}")
    return caminho


def gerar_checksum(caminho):
    """Etapa 3 (extra) - Calcula SHA-256 e salva em arquivo .sha256."""
    sha256 = hashlib.sha256()
    with open(caminho, "rb") as f:
        # Lê em blocos para não carregar o arquivo inteiro na memória
        for bloco in iter(lambda: f.read(65536), b""):
            sha256.update(bloco)
    digest = sha256.hexdigest()

    caminho_hash = caminho + ".sha256"
    with open(caminho_hash, "w") as f:
        # Formato compatível com: sha256sum -c arquivo.sha256
        f.write(f"{digest}  {os.path.basename(caminho)}\n")
    print(f"[OK] SHA-256: {digest}")
    print(f"[OK] Hash salvo em: {caminho_hash}")


def aplicar_retencao():
    """Etapa 4 - Remove backups com mais de DIAS_RETENCAO dias."""
    limite = time.time() - DIAS_RETENCAO * 24 * 60 * 60
    removidos = []

    for nome in os.listdir(DESTINO):
        if not nome.endswith(".tar.gz"):
            continue
        caminho = os.path.join(DESTINO, nome)
        if os.path.getmtime(caminho) < limite:
            os.remove(caminho)
            removidos.append(nome)
            # Remove também o .sha256 correspondente, se existir
            hash_assoc = caminho + ".sha256"
            if os.path.exists(hash_assoc):
                os.remove(hash_assoc)
                removidos.append(nome + ".sha256")

    if removidos:
        print(f"[OK] Arquivos removidos (mais de {DIAS_RETENCAO} dias):")
        for nome in removidos:
            print(f"     - {nome}")
    else:
        print(f"[OK] Nenhum arquivo ultrapassou o período de retenção "
              f"de {DIAS_RETENCAO} dias.")


def ajustar_permissoes():
    """Etapa 5 (extra) - 700 nos diretórios e 600 nos arquivos de /backup/."""
    for pasta, subpastas, arquivos in os.walk(RAIZ_BACKUP):
        os.chmod(pasta, 0o700)
        for arquivo in arquivos:
            os.chmod(os.path.join(pasta, arquivo), 0o600)
    print(f"[OK] Permissões ajustadas em {RAIZ_BACKUP} "
          f"(diretórios 700, arquivos 600)")


def main():
    verificar_root()
    print("=== Início do backup:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "===")
    criar_diretorio()
    arquivo = gerar_backup()
    gerar_checksum(arquivo)
    aplicar_retencao()
    ajustar_permissoes()
    print("=== Backup finalizado com sucesso ===")


if __name__ == "__main__":
    main()
