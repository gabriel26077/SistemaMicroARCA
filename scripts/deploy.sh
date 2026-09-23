#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

dry_run=false
bootstrap=false
dns_args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=true ;;
    --bootstrap) bootstrap=true ;;
    --cloudflare) dns_args=(--cloudflare) ;;
    *) echo 'Uso: scripts/deploy.sh [--dry-run] [--bootstrap] [--cloudflare]' >&2; exit 2 ;;
  esac
done

clean_tree() {
  [[ -z "$(git status --porcelain --untracked-files=all)" ]] || {
    echo 'ERRO: faça commits locais de todas as mudanças antes do deploy.' >&2; exit 1;
  }
}
clean_tree
commit=$(git rev-parse --verify HEAD)
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || exit 1
python3 -m unittest discover -s tests -v
python3 scripts/validate_catalog.py
python3 scripts/build_catalog.py
python3 scripts/build_catalog.py --check
git diff --check
clean_tree
[[ "$(git rev-parse HEAD)" == "$commit" ]] || { echo 'HEAD mudou durante validação.' >&2; exit 1; }
digest=$(python3 scripts/remote_release.py digest dist)
token=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
incoming="/var/www/MicroARCA-libs/.incoming-$commit-$token"

if "$dry_run"; then
  echo "DRY-RUN: validações locais concluídas; nenhuma conexão SSH ou escrita remota."
  echo "Preparar $incoming em vps; transferir dist/ usando rsync por SSH."
  echo "Verificar SHA-256 $digest e imutabilidade contra releases anteriores."
  echo "Publicar releases/$commit e trocar current atomicamente; preservar releases."
  echo "Validação DNS selecionada: ${dns_args[*]:-direta}; será executada somente no deploy real."
  exit 0
fi

# Infrastructure provisioning is deliberately separate; this only publishes files.
# Cloudflare requires an explicit flag; the default still requires direct DNS.
remote_ips=$(ssh -o BatchMode=yes -o ConnectTimeout=10 vps hostname -I)
python3 scripts/check_dns.py --origin-ips "$remote_ips" "${dns_args[@]}"
remote() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 vps \
    python3 - "$1" "$commit" "$token" "$digest" < scripts/remote_release.py
}
prepared=false
cleanup() {
  status=$?
  trap - EXIT
  if "$prepared"; then
    remote abort || echo "Limpeza remota pendente; inspecione .deploy-lock e $incoming." >&2
  fi
  exit "$status"
}
trap cleanup EXIT
prepared=true
remote prepare
rsync -rlt --checksum --chmod=D755,F644 --no-links \
  -e 'ssh -o BatchMode=yes -o ConnectTimeout=10' dist/ "vps:$incoming/"
remote finalize
prepared=false
if "$bootstrap"; then
  echo 'Release completo ativado para o primeiro provisionamento do Caddy.'
  echo 'Verificação HTTPS pendente: após configurar Caddy, execute python3 scripts/verify_public.py.'
  exit 0
fi
echo 'Transferência e ativação concluídas. Verificando o endpoint público...'
python3 scripts/verify_public.py
