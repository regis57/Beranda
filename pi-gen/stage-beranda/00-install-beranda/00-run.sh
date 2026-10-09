#!/bin/bash -e
# Runs on the HOST building the image (not yet inside the Pi's filesystem): copies this
# repository's checkout into the image so the next script (00-run-chroot.sh) can install it
# with install.sh --source, exactly as a developer would with "install.sh --source .". Using
# the checkout that is actually being built from (set in BERANDA_SRC by the CI workflow, or
# defaulting to this repository as checked out on your own machine) means the image always
# matches the commit it was built from, instead of re-downloading whatever "main" is that day.

SRC="${BERANDA_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
install -d "${ROOTFS_DIR}/opt/beranda-src"
rsync -a --delete --exclude .git --exclude build --exclude '__pycache__' \
    "${SRC}/" "${ROOTFS_DIR}/opt/beranda-src/"
