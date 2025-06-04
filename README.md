Frontend repo : https://github.com/sandalu-umayanga/3yp-railLynk-front

Deployed Frontend Domain : https://main.dc21kqnkqpsk8.amplifyapp.com/



# 🚆 RailLynk – Smart Ticketing and Train Tracking System

RailLynk is an innovative digital solution designed to modernize the Sri Lankan railway system by introducing a smart, secure, and efficient way to manage ticketing and train tracking. It includes a card-based tap-in/tap-out ticketing system, real-time train monitoring, role-based dashboards, and secure data handling.

---

## 🔷 Project Overview

RailLynk replaces outdated manual railway operations with a fully digital, user-friendly, and scalable system. It is designed with inclusivity in mind, ensuring even non-tech-savvy users can navigate the platform using familiar tools like smart cards.

**Core Highlights:**
- Tap-in/Tap-out smart card ticketing.
- Real-time train tracking with animated visualizations.
- Role-specific dashboards for Admins, Station Managers, Drivers, and Passengers.
- GPS-based location updates and accident alerts.
- Secure backend with JWT and RBAC.

---

## 🔧 Technologies Used

### Frontend
- **Framework**: React
- **Libraries**: Leaflet (for maps), Axios, React Router
- **Security**: Protected Routes, JWT Token Validation, Role-Based Access

### Backend
- **Framework**: Django (REST API)
- **Database**: PostgreSQL
- **Security**: JWT Authentication, Role-Based Access Control (RBAC)

### Hardware
- **Microcontroller**: ESP32 (low-cost, highly capable)
- **Connectivity**: GPS Module + GSM/4G modules

### DevOps
- **CI/CD**: GitHub Actions
- **Deployment**: AWS Amplify (Frontend), Choreo/AWS EC2 (Backend)

---

## 🎭 Role-Based Features

### Admin
- Register passengers and stations.
- Full access to system management.

### Station Manager
- Register passengers and drivers.
- Manage recharges, ticket issuance, and schedules.

### Passenger
- Tap-in/out using smart card.
- View transaction history, travel logs, and recharge balance.

### Driver
- Send location updates.
- Notify about delays, landslides, or accidents.

---

## 🔐 Security Measures

### Frontend
- Protected routes via React Router.
- JWT token validation before accessing sensitive pages.

### Backend
- JWT token authentication.
- Role-Based Access Control (RBAC) for all endpoints.

### Card Security
- Card data is encrypted using custom encryption methods to prevent duplication and tampering.

---

## 🗺️ Real-Time Train Tracking

- Periodic polling from ESP32 devices to fetch GPS location.
- Animated movement on map using Leaflet.
- Stop durations and ETA visible to passengers and stations.
- Offline fallback: last known location + schedule estimation.

---

## 🧩 System Architecture

- Component-based frontend with separate panels for each role.
- REST API backend for data handling and control.
- Microservices for train location updates, notifications, and card transactions.

---

## ✅ Testing & Validation

- **Frontend Validation**: Form validations with error handling.
- **CI/CD**: GitHub Actions test every pull request.
- **Preview Deployments**: AWS Amplify preview builds for all branches.

---

## 🚧 Challenges and Solutions

| Challenge | Solution |
|----------|----------|
| No WebSocket support | Used periodic polling with mobile API |
| Internet/GPS instability | Buffer + fallback mode in ESP32 |
| Multiple roles with different access | JWT + RBAC |
| Integration with old infrastructure | Designed for parallel operation |
| Elderly user inclusion | Physical smart card recharge and usage |
| Hardware cost | Used ESP32 instead of expensive boards |
| Card duplication risk | Encrypted card data |

---

## 📎 CAD Design and Prototyping

Our smart gate hardware is currently being 3D printed using custom CAD designs. These will be integrated with the ESP32 and card reader system.


