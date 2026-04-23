# Clinic Professional Management System
## Development Plan

Project Name:
Clinic Lanud Professional Clinic System

Goal:
Build a professional hospital-grade clinic management system with patient database, electronic medical record, billing, and patient card printing with QR code and barcode.

---

# Core Modules

## 1. Patient Management
- Register patient
- Edit patient data
- Search patient
- Patient ID auto generation
- Patient status tracking
- **Scan-to-View Logic**:
    - **Physical Scanner**: Support for standard HID (Keyboard emulation) scanners.
    - **Camera/Webcam**: Browser-based scanning using `html5-qrcode` (Supported on Laptop/PC/Tablet).
    - Barcode: Autofills search bar and triggers lookup.
    - QR Code: Encodes direct URL to patient medical record (Internal/VPN only).
- **Registration Fee Tracking**:
    - Default $0 USD (Manual entry if applicable).
    - Optional field during registration/edit.

## 2. Patient Card System
- Landscape patient card
- QR code generation
- Barcode generation
- Card printing using Pointman printer
- Card reprint feature

## 3. Electronic Medical Record
- Patient history
- Diagnosis
- Doctor notes
- Prescription
- Visit history

## 4. Appointment System
- Doctor schedule
- Patient booking
- Queue management (Daily Reset)
- Automated queue numbering

## 5. Billing System
- Treatment billing
- Medicine billing
- Invoice generation
- Payment tracking
- **Registration Fee Integration**: Track registration deposits or fees paid in USD.

## 6. Pharmacy Module
- Medicine inventory
- Stock management
- Prescription dispensing

## 7. Laboratory Module
- Lab request
- Lab result management
- Result history

## 8. Staff Management
- Doctor profiles
- Staff accounts
- Role-based access control

## 9. Reporting System
- Patient statistics
- Financial reports
- Visit reports

---

# Technology Stack

Backend
Python 3.11
Django 4.x

Database
PostgreSQL

Frontend
HTML5
Bootstrap
JavaScript
**html5-qrcode** (For Laptop/PC Camera Scanning)

Libraries
qrcode
python-barcode
pillow
weasyprint

Infrastructure
Ubuntu Linux Server
Docker
Nginx
Gunicorn

---

# Card Specification (Visual Reference: /assets/)

**Card Type**: CR80 (85.60 mm × 53.98 mm)
**Orientation**: Landscape
**Theme**: White background with circular ripple patterns (from `depang.png`).

### Front Side (`depang.png`)
- **Top Center**: Logo (`Logo.png`) + Text "Clinic BairoPite Lanud" & "Community Health Care East Timor".
- **Middle Left**:
    - Patient ID: `MDXXXXXX`
    - DOB: `DD / MM / YYYY`
    - ADDRESS: (Text)
- **Lower Center**: **NARAN PASIENT** (Bold, Large font).

### Back Side (`belakan.png`)
- **Header**: Mini logo and clinic text.
- **Content**: Mission statement (Spirit of Dr. Daniel Murphy) and 4 points of instructions in Tetum.
- **Bottom Right**: **Verification QR Code**.
- **Bottom Left**: "Saude iha ita nia liman rasik." text.

---

# System Architecture

User Browser (Frontend)
↓
Django Web Application (Backend)
↓
Application Services & Business Logic
↓
Database (PostgreSQL)

---

## Card Printing Workflow (The Bridge Solution)

As web browsers cannot access local USB printers directly, the system uses a **Local Print Agent** approach:

1. **Backend**: Generates Card Image (Pillow) or PDF (WeasyPrint).
2. **Frontend**: Sends print command via WebSocket or Local API request.
3. **Local Print Agent**: A lightweight Python (FastAPI/PyQT) service running on the PC connected to the Pointman printer.
    - Listens on `localhost:8080`.
    - Receives image data.
    - Sends raw commands to Pointman SDK/Driver.
4. **Pointman Printer**: Executes physical card printing.

---

# Integrated Service Stack
- Django (Web Core)
- Local Print Agent (Hardware Bridge)
- PostgreSQL (Primary DB)
- Redis (Session & Queue)
- Nginx (Proxy)

---

# Project Folder Structure

clinic-system

backend/
patients/
appointments/
billing/
pharmacy/
laboratory/
printing/

templates/
cards/
patients/

static/

media/
qrcode/
barcode/

docs/

---

# Development Phases

Phase 1
System architecture setup

Phase 2
Patient management module

Phase 3
Medical record system

Phase 4
Card generation system

Phase 5
Printer integration

Phase 6
Reporting system

Phase 7
Deployment

---

# Security

Role based access control
Encrypted backups
Audit logging
HTTPS communication

---

# Scalability

Support 100,000+ patients
Multi clinic support
Cloud ready