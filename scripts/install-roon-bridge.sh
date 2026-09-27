#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo ./scripts/install-roon-bridge.sh"
  exit 1
fi

case "$(uname -m)" in
  aarch64) installer="roonbridge-installer-linuxarmv8.sh" ;;
  armv7l) installer="roonbridge-installer-linuxarmv7hf.sh" ;;
  *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
esac

temp_dir=$(mktemp -d)
trap 'rm -rf "${temp_dir}"' EXIT
curl --fail --location --output "${temp_dir}/${installer}" "https://download.roonlabs.com/builds/${installer}"
chmod +x "${temp_dir}/${installer}"
"${temp_dir}/${installer}"
