<img width="1557" height="1032" alt="Screenshot 2026-05-10 165012" src="https://github.com/user-attachments/assets/82d566af-1691-419b-bac1-57f4044e7eb9" />
File Integrity Checker
Internship Task 1 - CODTECH IT SOLUTIONS

Description
This is a professional Python-based security tool designed to monitor and ensure the integrity of files. It uses cryptographic hashing to detect any unauthorized modifications, additions, or deletions within a specified directory. It serves as a basic Host Intrusion Detection System (HIDS).

Features
Hashing Algorithm: Uses SHA-256 for secure and unique file fingerprinting.

Baseline Management: Creates a secure "Known Good State" of your files.

Real-Time Detection: Identifies when files are Added, Modified, or Removed.

Logging: Maintains a log of all integrity violations for auditing.

Technical Stack
Language: Python 3.x

Libraries: hashlib, os, json, argparse

How to Use
Initialize Baseline: python integrity_checker.py init .

Check Integrity: python integrity_checker.py check .

Monitor (Watch Mode): python integrity_checker.py watch .
