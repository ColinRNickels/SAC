# SAC
System to allow access to a Makerspace or other Studio.

## Project Overview
This repository will host an open-source makerspace access kiosk designed for Raspberry Pi. The system provides a swipe-to-enter workflow, local user management, certifications, and analytics, all running offline after setup.

## Requirements & Architecture
See the consolidated requirements and initial architecture notes in:
- [docs/requirements.md](docs/requirements.md)

## Development Quickstart
1. Create a virtualenv and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the API server:
   ```bash
   export SAC_ADMIN_TOKEN=change-me
   python -m sac.app
   ```

The service stores data in `sac/kiosk.db` by default. Override with `SAC_DB_PATH`.

## Local Test Environment (PC)
See [testing.md](testing.md) for step-by-step local PC setup and reset instructions.

## Raspberry Pi Setup (Fresh OS)
This guide targets a Raspberry Pi running Raspberry Pi OS Lite (64-bit) on a Pi with Ethernet or Wi-Fi.

### 1) Flash Raspberry Pi OS and enable SSH
1. Open **Raspberry Pi Imager** on your workstation.
2. Select **Raspberry Pi OS Lite (64-bit)**.
3. Click the gear icon (advanced options):
   - Set hostname (example: `sac-kiosk`)
   - Enable SSH (password auth is OK for first boot)
   - Configure Wi-Fi SSID/password and locale/timezone
4. Write the image to the SD card.
5. Boot the Pi and SSH in.

### 2) System packages
```bash
sudo apt update
sudo apt install -y git python3 python3-venv
```

### 3) Clone and install the kiosk service
```bash
git clone <YOUR_REPO_URL> SAC
cd SAC
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Run the service
```bash
source .venv/bin/activate
export SAC_ADMIN_TOKEN=change-me
python -m sac.app
```
The kiosk UI is at `http://<pi-ip-address>:5000/` and the admin console is at `http://<pi-ip-address>:5000/admin`.

### 5) (Optional) Run on boot with systemd
Create a service file:
```bash
sudo tee /etc/systemd/system/sac.service >/dev/null <<'EOF'
[Unit]
Description=SAC Makerspace Kiosk
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/SAC
Environment=SAC_DB_PATH=/home/pi/SAC/sac/kiosk.db
Environment=SAC_ADMIN_TOKEN=change-me
ExecStart=/home/pi/SAC/.venv/bin/python -m sac.app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sac.service
sudo systemctl start sac.service
```

## Building a Preconfigured Image (Raspberry Pi Imager)
You can build a ready-to-flash image by preparing a “golden” SD card and then cloning it.

### 1) Prepare the golden SD card
1. Use Raspberry Pi Imager to flash **Raspberry Pi OS Lite (64-bit)** to an SD card.
2. Boot the Pi from this SD card and complete **Raspberry Pi Setup** steps above.
3. Confirm the service runs with `python -m sac.app` or `systemctl status sac.service`.
4. Shut down the Pi cleanly.

### 2) Create an image from the SD card
On a Linux or macOS workstation, use Raspberry Pi Imager:
1. Insert the SD card into your workstation.
2. In Raspberry Pi Imager, choose **Use custom** and select **Create Image from SD card**.
3. Save the resulting `.img` file.

### 3) Distribute and flash
Share the `.img` file with your team. Anyone can flash it with Raspberry Pi Imager by selecting **Use custom** and choosing the image.

> Tip: If you need multiple target devices with different hostnames or Wi-Fi settings, keep the image minimal and use the Imager advanced options at flash time to customize each device.
