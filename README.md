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
   python -m sac.app
   ```

The service stores data in `sac/kiosk.db` by default. Override with `SAC_DB_PATH`.
