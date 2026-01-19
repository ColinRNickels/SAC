# Makerspace Access Kiosk — Requirements & Initial Architecture

## Goals
- Provide a **kiosk-first** swipe-to-enter experience for makerspaces and studios.
- Offer an **admin console** reachable over the device’s local access point for user management, certifications, and analytics.
- Run **locally on a Raspberry Pi** (Pi Touchscreen 2) using a **Python + SQLite** stack.
- Support **offline operation** after first setup (no internet required for daily use).
- Be **open-source under GPLv3** with comprehensive setup documentation.

## Personas & Roles
- **Student**: Can swipe to check access and tool certifications.
- **Student Staff**: Can access backend for user management and approvals; **cannot** create certifications.
- **Admin**: Full access to analytics, certification management, and system settings.

## Primary Workflows
### 1. Swipe-to-enter (kiosk)
- Accepts input from a USB HID barcode/QR reader (appears as keyboard text).
- Matches input against **campus ID** (unique) and also allows lookup by email.
- On swipe, staff can choose the **target certification** (space access or specific tool) and get a pass/fail response.

### 2. New user onboarding
- User swipes ID, agrees to terms, and enters:
  - First name
  - Last name
  - Email address
  - Terms acceptance
- User is created as **pending** until a staff member approves.

### 3. Staff approval
- Staff reviews pending users in admin console.
- Staff approves/denies user access.

### 4. Certifications
- Certifications are **non-hierarchical** and **non-expiring**.
- Only staff or admins can grant/revoke certifications.
- Certifications can be for:
  - Space access
  - Specific tools (e.g., bandsaw, miter saw, hand tools)

### 5. Analytics & Reporting
- **Counts over time**:
  - Swipes per day/week/month
  - Swipes per hour
  - Unique users per day/week/month
- **Heatmap**: Day-by-hour activity visualization.
- **Cert usage**: Which tools/certifications are most requested.
- **Export**: CSV export from the admin portal.

## Terms of Use
- A **single, current terms file** stored separately and easily updated.
- No versioning or acceptance history required for v1.

## System Requirements
### Hardware
- Raspberry Pi
- Raspberry Pi Official Touchscreen 2 (portrait orientation)
- USB HID barcode/QR reader
- 3D-printed enclosure

### Software
- Python web application
- SQLite database (local)
- Web UI for kiosk + admin console
- Local access point for admin access

## Networking & Setup
### First Boot
- CLI-based setup:
  - Admin username/password
  - Wi-Fi credentials (initial connectivity)
  - Configure device access point

### Operation
- Runs offline after setup.
- Hosts local access point for admin access.
- Device UI defaults to **portrait**.

## Future Direction (Non-goals for v1)
- Multi-device support via **central server** with thin clients.
- Captive portal onboarding.
- USB-based backups.

## Proposed High-Level Architecture (v1)
- **Frontend**: Kiosk UI + Admin UI (served locally).
- **Backend**: Python web server (Flask/FastAPI or similar).
- **Database**: SQLite.
- **Input**: USB HID reader (keyboard events).

## Data Model (Initial)
- **User**: id, campus_id, email, first_name, last_name, status (pending/active), role.
- **Certification**: id, name, description, scope (space/tool).
- **UserCertification**: user_id, certification_id, granted_by, granted_at.
- **SwipeEvent**: user_id, input_value, certification_checked, timestamp, result.
- **Terms**: current_terms_text (or file path reference).

## Open Questions (for later)
- Exact analytics visualization library and UI layout.
- Whether time sync should rely on RTC or first-boot NTP.
- Admin role separation of user management vs analytics screens.
