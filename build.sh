#!/usr/bin/env bash

set -euo pipefail
shopt -s globstar 
# set -x

for f in ./scripts/lib/**/*; do
	[[ -f $f ]] && . $f
done

source ./scripts/common/colors
source ./scripts/common/environment

[[ $EUID -ne 0 ]] && _error "Build script requires root privilages. Try again with sudo." \
                  && exit 1

install_dependencies
populate_buildDir
gen_livebuild_conf
populate_chrootDir

# Third-party repositories
_warn "Adding extra repositoriies"
cp -r $SRC_DIR/archives/* $LB_CONFIG_DIR/archives/

# Calamares Installer
_warn "Adding calamares configs"
cp -r $SRC_DIR/calamares/ $CHROOT_DIR/etc/

# Copy bootloader configurations
_warn "Adding bootloader configs"
cp -r $SRC_DIR/bootloaders/* $LB_CONFIG_DIR/bootloaders/

# Hooks
_warn "Adding lb hooks"
cp -r $SRC_DIR/hooks/normal/* $LB_CONFIG_DIR/hooks/normal/

# Dotfiles
_warn "Adding user-specific configs"
cp -r $SRC_DIR/flavors/xfce/skel/menus		$CHROOT_DIR/etc/skel/.config/	# menu configurations
cp -r $SRC_DIR/flavors/xfce/skel/Thunar  	$CHROOT_DIR/etc/skel/.config/	# thunar custom actions
cp -r $SRC_DIR/flavors/xfce/skel/xfce4		$CHROOT_DIR/etc/skel/.config/	# xfce configurations
cp -r $SRC_DIR/flavors/xfce/skel/gtk-3.0	$CHROOT_DIR/etc/skel/.config/	# gtk css
cp -r $SRC_DIR/flavors/xfce/skel/Kvantum	$CHROOT_DIR/etc/skel/.config/	# kvantum 
cp -r $SRC_DIR/flavors/xfce/skel/.bash* 	$CHROOT_DIR/etc/skel/		# bash configurations
cp -r $SRC_DIR/flavors/xfce/skel/.xscreensaver 	$CHROOT_DIR/etc/skel/		# screensaver
cp -r $SRC_DIR/flavors/xfce/skel/.face* 	$CHROOT_DIR/etc/skel/		# profile mugshot

# ShopnoOS xfce4-panel-profile
cp -r $SRC_DIR/flavors/xfce/panel/* 		$CHROOT_DIR/etc/skel/.local/share/xfce4-panel-profiles/	# panel profile

# xscreensaver
cp -r $SRC_DIR/flavors/xfce/screensaver/* 	$CHROOT_DIR/etc/skel/.local/share/screensaver/	# panel profile

# Desktops
cp -r $SRC_DIR/desktops/*.desktop 		$CHROOT_DIR/usr/local/share/applications/	# Modified desktops

# Scripts
cp -r $SRC_DIR/scripts/*        $CHROOT_DIR/usr/local/bin/     		# scripts

# Desktop backgrounds & icons
cp -r $SRC_DIR/backgrounds/*    $CHROOT_DIR/usr/share/backgrounds/	# wallpapers
cp -r $SRC_DIR/icons/*          $CHROOT_DIR/usr/share/icons/		# wallpapers

# Drivers:
# RTL8821CE
# cp -r $SRC_DIR/drivers/*        $CHROOT_DIR/usr/src/        		# Wlan driver

# Appearance
cp -r $SRC_DIR/flavors/xfce/themes/* 		$CHROOT_DIR/usr/share/themes/	# GTK theme
cp -r $SRC_DIR/flavors/xfce/icons/* 		$CHROOT_DIR/usr/share/icons/	# Icon & cursor theme
cp -r $SRC_DIR/flavors/xfce/kvantum/ 		$CHROOT_DIR/usr/share/Kvantum/	# kvantum theme

# Package lists
_warn "Generating package-lists"
echo "calamares calamares-settings-debian" > $LB_CONFIG_DIR/package-lists/calamares.list.chroot

# Include additional repositories
# mkdir -p $_workingDir/$_buildCache/config/archives/

# INSTALL DESKTOP AND APPLICATIONS FOR STANDARD BUILD
# Display manager
echo "lightdm lightdm-settings" > $LB_CONFIG_DIR/package-lists/display-manager.list

# Multimedia
echo "mpv pavucontrol vlc" > $LB_CONFIG_DIR/package-lists/multimedia.list

# IDEs and codeeditors
echo "arduino codeblocks code geany sublime-text" > $LB_CONFIG_DIR/package-lists/development.list.chroot

# Desktop Environment: XFCE4
echo "evince galculator  thunar thunar-archive-plugin thunar-data thunar-font-manager thunar-media-tags-plugin thunar-volman xfce4 xfce4-notifyd xfce4-terminal xfce4-panel-profiles xfce4-power-manager ristretto xscreensaver xfce4-battery-plugin xfce4-clipman-plugin xfce4-cpufreq-plugin xfce4-cpugraph-plugin xfce4-datetime-plugin xfce4-diskperf-plugin xfce4-fsguard-plugin xfce4-genmon-plugin xfce4-mailwatch-plugin xfce4-netload-plugin xfce4-places-plugin xfce4-screenshooter xfce4-sensors-plugin xfce4-smartbookmark-plugin xfce4-systemload-plugin xfce4-timer-plugin xfce4-wavelan-plugin xfce4-weather-plugin xfce4-xkb-plugin xfce4-whiskermenu-plugin xarchiver mugshot mousepad tumbler" > $LB_CONFIG_DIR/package-lists/xfce.list.chroot

# Themes and icons
echo "breeze-gtk-theme breeze-icon-theme qt5-style-kvantum" > $LB_CONFIG_DIR/package-lists/apprearance.list.chroot

# Internet
echo "google-chrome-stable" > $LB_CONFIG_DIR/package-lists/internet.list.chroot

# Fonts and input
echo "fonts-beng fonts-noto-core fonts-noto-extra fonts-noto-ui-core fonts-noto-ui-extra fonts-noto-color-emoji ibus-avro" > $LB_CONFIG_DIR/package-lists/input-methods.list.chroot

# Extra packaages
echo "google-chrome-stable flatpak gnome-software-plugin-flatpak jq accountsservice bc dconf-cli gnome-disk-utility gnome-nettool gnome-system-tools gnome-software gvfs-backends gvfs-fuse intel-media-va-driver light-locker network-manager-gnome network-manager-openconnect-gnome network-manager-openvpn-gnome pavucontrol pulseaudio pulseaudio-module-bluetooth xdg-utils systemd-timesyncd module-assistant build-essential bash-completion alsa-utils apt-transport-https autoconf automake bluetooth bluez bluez-tools blueman btrfs-progs cdtool cdrdao cdrskin cifs-utils clonezilla cryptsetup cryptsetup-initramfs cups cups-filters curl dbus-user-session dbus-x11 debconf debhelper dh-autoreconf dialog dirmngr dkms dvdauthor exfatprogs faad fakeroot ffmpeg flac foomatic-db foomatic-db-engine frei0r-plugins fuse3 gdebi git ghostscript gimp inkscape gir1.2-ibus-1.0 gparted grub-pc gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-plugins-good hardinfo haveged htop  ibus ibus-data ibus-gtk ibus-gtk3 iftop im-config inxi isolinux iw jfsutils lame less libibus-1.0-5 libqt5opengl5 libnss-mdns libsmbclient libxcb-xtest0 libxvidcore4 linux-headers-amd64 live-build lsb-release lshw menu mjpegtools mpg321 mtools mythes-en-us netcat-openbsd ntfs-3g openconnect openvpn openvpn-systemd-resolved os-prober p7zip-full pciutils perl  printer-driver-gutenprint python3-ibus-1.0 python3-psutil samba-common-bin simple-scan  sox squashfs-tools streamripper sudo syslinux syslinux-common system-config-printer testdisk timeshift udisks2 upower unzip vim wget x265 x264 xclip xcape xfsprogs xorg xserver-xorg-input-all xserver-xorg-video-all xorriso yad zenity zip zstd" > $LB_CONFIG_DIR/package-lists/extrapackages.list.chroot

# Firmwares and Drivers
echo "atmel-firmware bluez-firmware firmware-linux-free firmware-misc-nonfree firmware-amd-graphics firmware-atheros firmware-bnx2 firmware-bnx2x firmware-brcm80211 firmware-cavium firmware-intel-sound firmware-iwlwifi firmware-libertas firmware-linux firmware-linux-nonfree firmware-misc-nonfree firmware-myricom firmware-netronome firmware-netxen firmware-qcom-media firmware-qcom-soc firmware-qlogic firmware-realtek firmware-samsung firmware-siano firmware-ti-connectivity firmware-sof-signed firmware-zd1211" > $LB_CONFIG_DIR/package-lists/firmware.list.chroot

# Printers
echo "cups cups-filters printer-driver-all system-config-printer" > $LB_CONFIG_DIR/package-lists/printers.list

# ShopnoOS specific meta-packages
echo "jadupc-remote-support-console shopno-os-base shopno-os-looks shopno-os-log-sync shopno-os-stats-sync shopno-os-debug shopno-os-games shopno-os-refresh-menu" > $LB_CONFIG_DIR/package-lists/jadupc.list.chroot
# echo "jadupc-remote-support-console shopno-os-base shopno-os-refresh-menu" > $LB_CONFIG_DIR/package-lists/jadupc.list.chroot


# Bootloaders and stuff
echo "efibootmgr grub-common grub-pc-bin grub2-common grub-efi-amd64 grub-efi-amd64-bin grub-efi-amd64-signed grub-efi-ia32-bin libefiboot1 libefivar1 mokutil os-prober shim-helpers-amd64-signed shim-signed shim-signed-common shim-unsigned" > $LB_CONFIG_DIR/package-lists/grubs.list.binary


# CREATE FOLDERS IN THE CHROOT
# cd $_workingDir

# ShopnoOS release
# source ./libs/mods/os-release
# source ./libs/mods/iso-release
_info "Populating release files"
populate_iso_release
populate_os_release

# resolv.conf
_info "Populating resolv.conf"
populate_resolv_conf

# dpkg vendor
# source ./libs/mods/dpkg-vendor
_info "Populating dpkg-vendor"
populate_dpkg_vendor

# enable sudo password feedback
# source ./libs/mods/password-feedback
_info "Enabling password feedback"
populate_sudoers

# apt conf
# source ./libs/mods/apt-conf
_info "Populating apt-conf"
populate_apt_conf
populate_apt_source

# Local packages (SUPPORTS .udeb files NOT GENERIC .deb)
# Include packages in the misc64 folder
cp $SRC_DIR/deb/* $CHROOT_DIR/

# Start build
# cd $_buildCache
lb build
