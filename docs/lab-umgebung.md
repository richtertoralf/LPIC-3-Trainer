# LAB-Umgebung einrichten

Die Fach-LABs des LPIC-3-Trainers werden in einer eigenen Testumgebung bearbeitet, die du selbst aufbaust und betreibst. Diese Anleitung gibt Orientierung: Was du brauchst, wie eine bewährte Umgebung aussieht und woran du erkennst, dass sie funktioniert. Sie schreibt dir nicht jeden Handgriff vor. Wie du die Umgebung konkret realisierst, entscheidest du. Der Trainer selbst stellt keine Maschinen bereit und führt nichts aus.

**Grundregel:** LABs nur auf Testsystemen, nie auf produktiven Rechnern, nie im Firmen- oder Schulnetz ohne Absprache. Viele Aufgaben ändern Netzwerk-, Speicher- oder Sicherheitseinstellungen tief im System.

## 1. Empfohlene Umgebung im Überblick

- Ein Linux-Rechner oder -Notebook als Host (Debian, Ubuntu oder eine andere aktuelle Distribution).
- Virtualisierung mit KVM/QEMU und libvirt.
- Verwaltung mit `virt-manager` (grafisch) und/oder `virsh` (Kommandozeile).
- Zwei bis drei virtuelle Maschinen mit Debian 12/13 oder Ubuntu 24.04 LTS.
- Ein isoliertes virtuelles Netzwerk für die VMs, zusätzlich NAT für Paketinstallationen.
- Bei Bedarf eine kleine Linux-VM als Router zwischen zwei Netzen.
- Zusätzliche virtuelle Festplatten für Storage-LABs (LVM, RAID, DRBD, iSCSI, Ceph-Grundlagen).
- Snapshots vor jedem LAB, damit du jederzeit zum Ausgangszustand zurückkehren kannst.

Andere Plattformen sind zulässig: VirtualBox, VMware Workstation/Fusion, Proxmox VE, Hyper-V, UTM auf macOS oder ein Cloud-Konto mit eigenen VMs. Die LABs setzen nur voraus, dass du mehrere Linux-Systeme mit Root-Rechten, eigenem Netz und zusätzlichen Datenträgern hast. KVM/libvirt ist eine Empfehlung, keine Pflicht.

## 2. Hardwarevoraussetzungen

| Ressource | Minimum | Empfehlung |
|---|---|---|
| CPU | 2 Kerne mit Hardwarevirtualisierung (Intel VT-x oder AMD-V) | 4 Kerne oder mehr |
| RAM | 8 GB (Host 2 GB + 2 VMs à 2 GB) | 16 GB oder mehr (3 VMs, Samba-AD braucht 2 GB) |
| Festplatte | 40 GB frei | 100 GB frei, SSD |
| Netz | Internetzugang für Paketinstallationen | dazu ein Netz, in dem Testsysteme nichts stören |

Prüfen, ob die CPU Virtualisierung kann und ob sie im BIOS/UEFI aktiv ist:

```bash
grep -Ec '(vmx|svm)' /proc/cpuinfo     # > 0: CPU unterstützt Virtualisierung
sudo apt install cpu-checker && kvm-ok  # Ubuntu: "KVM acceleration can be used"
lsmod | grep kvm                        # Module kvm_intel oder kvm_amd geladen
```

Meldet `kvm-ok` „disabled by BIOS“, musst du VT-x/AMD-V in den Firmware-Einstellungen einschalten. In einer VM auf einem anderen Hypervisor brauchst du „nested virtualization“, sonst laufen die LAB-VMs nur sehr langsam.

## 3. Werkzeuge installieren

Debian/Ubuntu:

```bash
sudo apt install qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients \
  virtinst virt-manager bridge-utils
sudo usermod -aG libvirt,kvm "$USER"     # danach neu anmelden
virsh -c qemu:///system list --all       # leer, aber ohne Fehler
```

Nützlich dazu: `cloud-image-utils` (Cloud-Images mit cloud-init), `libguestfs-tools` (`virt-customize`, `virt-sysprep`) und `openssh-client`. Alternativ oder zusätzlich lässt sich Vagrant mit dem libvirt-Provider einsetzen, wenn du Umgebungen als Code beschreiben möchtest.

Dokumentation: `man virsh`, `man virt-install`, `man qemu-img`, die libvirt-Website (libvirt.org, Abschnitt „Networking“), das Debian-Wiki zu KVM sowie das Ubuntu Server Guide zu libvirt.

## 4. Virtuelle Maschinen erstellen

Drei gängige Wege, alle gleichwertig:

1. **Installation von ISO** mit `virt-manager` oder `virt-install --cdrom`. Einfach, aber je VM 10 bis 15 Minuten Installationsdialog.
2. **Cloud-Image mit cloud-init.** Debian und Ubuntu liefern fertige `qcow2`-Images. Du legst eine kleine Datei mit Benutzer, SSH-Schlüssel und Hostnamen an und die VM ist nach einer Minute benutzbar. Beispiel:

```bash
wget https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2
qemu-img create -f qcow2 -b debian-12-generic-amd64.qcow2 -F qcow2 lab1.qcow2 20G
cat > user-data <<'EOT'
#cloud-config
hostname: lab1
users:
  - name: admin
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-ed25519 AAAA... dein-schluessel
EOT
cloud-localds seed.iso user-data
virt-install --name lab1 --memory 2048 --vcpus 2 --disk lab1.qcow2 --disk seed.iso,device=cdrom \
  --os-variant debian12 --network network=default --import --noautoconsole
```

3. **Vorlage klonen.** Eine fertig eingerichtete VM mit `virt-sysprep` bereinigen und mit `virt-clone` vervielfältigen. Schnell, wenn du mehrere gleichartige Maschinen brauchst.

Empfehlung für die LABs: eine Vorlage „Debian 12 minimal mit SSH, sudo, `vim`, `curl`“ bauen, daraus `lab1`, `lab2`, `lab3` klonen und von jeder einen Snapshot „frisch“ anlegen.

## 5. Virtuelle Netzwerke

libvirt kennt drei für die LABs relevante Netztypen:

| Typ | Verhalten | Einsatz |
|---|---|---|
| **NAT** (`default`, `virbr0`) | VMs erreichen das Internet über den Host, von außen sind sie nicht erreichbar; DHCP und DNS durch `dnsmasq` | Paketinstallation, Updates |
| **Isoliert** | VMs sehen nur sich gegenseitig und den Host, kein Weg nach außen | Samba-AD, DNS, DHCP, NFS, Firewall-LABs; alles, was im echten Netz stören würde |
| **Geroutet** oder **Bridge** | VMs hängen (geroutet oder direkt) im Netz des Hosts | nur, wenn du das Netz kontrollierst und es ausdrücklich erlaubt ist |

Ein isoliertes Netz ohne eigenen DHCP legst du mit einer XML-Datei an:

```xml
<network>
  <name>lab-isolated</name>
  <bridge name="virbr10"/>
  <ip address="192.168.56.1" netmask="255.255.255.0"/>
</network>
```

```bash
virsh net-define lab-isolated.xml && virsh net-start lab-isolated && virsh net-autostart lab-isolated
```

Für ein zweites Segment (z. B. 192.168.57.0/24) wiederholst du das mit anderem Namen, anderer Bridge und anderer Adresse. Jede LAB-VM bekommt typischerweise zwei Netzwerkkarten: eine im NAT-Netz (für `apt`) und eine im isolierten Netz (für das LAB). Viele LABs gehen von festen Adressen im Bereich 192.168.56.0/24 aus; passe sie an deine Umgebung an.

## 6. Ein einfacher virtueller Linux-Router

Für LABs mit zwei Netzen (Firewall, Routing, VPN, DHCP-Relay) genügt eine schlanke VM mit drei Schnittstellen: NAT-Netz nach außen, `lab-isolated` (192.168.56.0/24) und ein zweites isoliertes Netz (192.168.57.0/24).

Grundzüge auf dem Router:

```bash
# IP-Forwarding dauerhaft einschalten
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/90-router.conf && sudo sysctl --system
# Adressen der inneren Schnittstellen (Beispiel mit netplan/ifupdown/systemd-networkd nach Wahl)
#   enp2s0: 192.168.56.1/24      enp3s0: 192.168.57.1/24
# NAT nach außen, Weiterleitung zwischen den Netzen erlauben (nftables)
sudo nft add table inet nat
sudo nft 'add chain inet nat postrouting { type nat hook postrouting priority 100; }'
sudo nft add rule inet nat postrouting oifname "enp1s0" masquerade
```

Die anderen VMs bekommen den Router als Standardgateway (`192.168.56.1` bzw. `192.168.57.1`). Die libvirt-Netze selbst dürfen dann keine eigene Host-Adresse im gleichen Bereich haben, sonst gibt es zwei Gateways; lege sie in dem Fall ohne `<ip>`-Element an. Alternativ nutzt du für den Router eine spezialisierte Distribution (OpenWrt, VyOS), wenn du dich darauf konzentrieren willst.

## 7. Adressierung und Erreichbarkeit zwischen VMs

- Vergib feste Adressen oder feste DHCP-Zuordnungen (`virsh net-edit` mit `<host mac=... ip=.../>`), damit LAB-Anleitungen reproduzierbar bleiben.
- Trage die LAB-Hosts in `/etc/hosts` jeder VM ein (`192.168.56.10 lab1`), solange du keinen eigenen DNS betreibst. Die DNS- und AD-LABs ersetzen das später bewusst.
- Prüfe die Verbindung schrittweise: `ip -br addr`, `ip route`, `ping <Nachbar>`, `ss -tlnp` auf der Zielmaschine, `nc -vz <Ziel> <Port>`.
- Vom Host erreichst du VMs im NAT-Netz direkt über ihre `virbr0`-Adresse (`virsh domifaddr lab1`); im isolierten Netz über die Host-Adresse der Bridge, wenn du eine vergeben hast.

## 8. Zusätzliche virtuelle Datenträger

Storage-LABs (LVM, Software-RAID, DRBD, iSCSI, Dateisystem-Themen) brauchen leere Platten, die du gefahrlos partitionieren und überschreiben kannst.

```bash
qemu-img create -f qcow2 /var/lib/libvirt/images/lab1-data1.qcow2 5G
virsh attach-disk lab1 /var/lib/libvirt/images/lab1-data1.qcow2 vdb --persistent --subdriver qcow2
# in der VM:
lsblk            # vdb erscheint als neue, leere Platte
```

Zwei bis vier Platten à 5 GB je VM reichen für alle LABs. Benenne sie eindeutig und prüfe vor jedem zerstörenden Befehl (`mkfs`, `wipefs`, `dd`, `pvcreate`, `mdadm --create`) mit `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT`, dass du die richtige Platte triffst. Die Systemplatte `vda` wird nie angefasst.

## 9. Sicherheit und Abgrenzung vom produktiven Netz

- LAB-Dienste (DNS, DHCP, Samba-AD, Kerberos, NFS, iSCSI) nur im isolierten Netz anbieten. Ein zweiter DHCP- oder DNS-Server im Heim- oder Firmennetz stört andere Geräte.
- Bridge-Netze ins reale LAN nur mit Zustimmung des Netzbetreibers.
- Firewall-LABs über die Konsole (`virsh console`, virt-manager) bearbeiten, nicht nur über SSH: Eine falsche Regel sperrt dich sonst aus.
- Keine echten Zugangsdaten, Zertifikate oder Kundendaten in LAB-VMs verwenden. Testpasswörter dürfen einfach sein, weil das Netz isoliert ist; auf Systemen mit Internetzugang dennoch SSH nur mit Schlüssel.
- VMs, die im Internet erreichbar wären (Cloud, Bridge), aktuell halten und nach dem LAB abschalten.
- Der Host bleibt sauber: Dienste und Pakete der LABs gehören in die VMs, nicht auf den Host.

## 10. Snapshots und Zurücksetzen

Vor jedem LAB einen Ausgangszustand sichern:

```bash
virsh snapshot-create-as lab1 frisch "Grundinstallation mit SSH"   # intern (qcow2), VM kann laufen
virsh snapshot-list lab1
virsh snapshot-revert lab1 frisch                                  # zurück zum Ausgangszustand
```

Alternativen: VM ausschalten und die `qcow2`-Datei kopieren, oder Overlay-Images (`qemu-img create -b`) wie in Abschnitt 4. In VirtualBox und VMware heißen die Funktionen ebenfalls „Snapshot“. Für Dienste mit Datenbanken (Samba-AD, LDAP) ist ein Snapshot bei ausgeschalteter VM am zuverlässigsten.

## 11. Funktionsprüfung

Deine Umgebung ist bereit, wenn du jeden Punkt dieser Liste erfüllst:

1. `virsh list --all` zeigt deine VMs; eine VM startet in unter einer Minute und du kannst dich per SSH oder Konsole anmelden.
2. `sudo` funktioniert in der VM, `apt update` lädt Paketlisten (NAT-Netz).
3. Zwei VMs im isolierten Netz erreichen sich gegenseitig per `ping` und per Hostname (aus `/etc/hosts`).
4. Aus dem isolierten Netz kommst du **nicht** ins Internet (Isolation geprüft).
5. Eine zusätzliche Platte erscheint in der VM als `vdb` und lässt sich mit `mkfs.ext4 /dev/vdb` formatieren.
6. Ein Snapshot lässt sich anlegen; nach `snapshot-revert` ist eine zuvor angelegte Testdatei verschwunden.
7. Optional: Vom Netz 192.168.57.0/24 erreichst du über die Router-VM eine Maschine in 192.168.56.0/24.

Hält die Umgebung diese Prüfung stand, kannst du jedes Fach-LAB beginnen und nach dem LAB mit einem Snapshot-Revert sauber neu starten.

## 12. Weiterführende Quellen

- libvirt: Dokumentation zu Netzwerken und Storage auf libvirt.org.
- QEMU: `qemu-img`-Handbuch und Wiki.
- Debian-Wiki „KVM“, Ubuntu Server Guide „Virtualisation with QEMU“ und „libvirt“.
- cloud-init-Dokumentation (cloudinit.readthedocs.io) für automatisierte Erstkonfiguration.
- Die offiziellen LPI-Prüfungsziele der Module 300, 303, 305 und 306 nennen die Werkzeuge, mit denen die LABs arbeiten.
