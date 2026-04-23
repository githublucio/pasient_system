# AI Developer Prompt
Clinic Professional Management System

You are a senior Python Django software architect responsible for building a hospital-grade clinic management system.

The system must be scalable, secure, and production ready.

---

# System Description

Build a Django-based web system that includes:

Patient management
Electronic medical records
Appointment system
Billing system
Pharmacy module
Laboratory module
Patient card printing

The patient card must be landscape orientation and printable using a Pointman card printer.

---

# Technical Requirements

Backend
Python
Django

Database
PostgreSQL

Libraries
qrcode
python-barcode
pillow
weasyprint

Printer
Pointman card printer

---

# Patient Card Requirements

Orientation
Landscape

Front side

Clinic logo
Clinic name
Patient name
Patient ID
Date of birth
Address
QR code
Barcode

Back side

Clinic description
Card usage instructions
Emergency contact
Verification QR code

---

# Core Features

Patient registration
Patient search
Patient registration fee (USD) default $0
Patient dashboard
Medical record system
Doctor notes
Prescription management
Lab results
Card generation
Card printing

---

# Architecture Guidelines

Use clean architecture
Separate services
Reusable modules
Django apps structure

Example apps

patients
appointments
medical_records
billing
laboratory
pharmacy
printing

---

# Output Required

Generate:

Full Django project structure
Database models
API endpoints
Card templates
QR code generator
Barcode generator
Printer integration module

The system must be suitable for professional clinic use.