#!/bin/bash -e
# Runs chrooted into the Pi's own filesystem, as root - exactly like running install.sh
# yourself over SSH, except there is no SSH yet: this *is* what makes the image ready to
# flash and boot with no further setup. --with-wifi-setup is the point of this whole image:
# with no Wi-Fi configured, the Pi offers its own "Beranda setup" network on first boot.
/opt/beranda-src/install.sh --source /opt/beranda-src --with-wifi-setup
rm -rf /opt/beranda-src
# The copy has no git history (00-run.sh leaves .git out): make it a checkout of the repository
# so the Update button and a re-run of the install line can fetch into it later.
git -C /opt/beranda/src init -q
git -C /opt/beranda/src remote add origin https://github.com/regis57/Beranda.git
