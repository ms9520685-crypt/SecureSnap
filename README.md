# SecureSnap 

## Secure Stock Photo E-Commerce Platform

SecureSnap is a web application I built to explore how common cybersecurity practices can be applied to an online stock photo
e-commerce platform. The basic idea is simple: users can create an account, log in, browse stock photos, purchase photos, and download the photos they
have purchased.
Along with these basic features, I focused on adding security mechanisms that protect user accounts and digital content from
common web application attacks.

---

## Why I Built This

An online platform that sells digital content needs to protect more than just usernames and passwords. It also needs to make sure that
users cannot access content they have not purchased and that common web attacks are handled properly.
For this project, I wanted to understand how these security concepts work in an actual web application instead of only studying them
theoretically.

The main security areas I focused on were:
- Password protection
- User authentication
- Access control
- CSRF protection
- Brute-force protection
- Input validation
- SQL injection prevention
- XSS prevention
- Secure downloads
- Security logging


## Features

### User Registration

Users can create an account using a username and password.
Passwords are not stored directly in the database. Instead, they are hashed before being stored.

---

### User Login and Logout

Users can securely log in and log out of the application.
Flask-Login is used to manage user sessions and protect pages that should only be accessible to authenticated users.

---

### Stock Photo Browsing

After logging in, users can browse the available stock photographs.

Each photograph has:

- Title
- Description
- Price
- Preview image

---

### Photo Purchases

Users can purchase a photograph through the application.

The application also checks whether the user has already purchased the same photograph to prevent duplicate purchases.

---

### Protected Downloads

A user cannot download a photograph just because they are logged in.

Before allowing a download, SecureSnap checks whether the current user has actually purchased that photograph.

If they have not purchased it, the application returns a `403 Forbidden` response.

---

# Security Features

## 1. Password Hashing

Passwords are never stored as plain text.

SecureSnap uses Werkzeug's password hashing functions:

 python
generate_password_hash()
check_password_hash()

When a user registers, their password is converted into a secure
hash before being stored in the database.

During login, the entered password is compared with the stored hash.

## 2. Authentication

Flask-Login is used to handle user authentication and sessions.

Important pages such as the photo store and photo details require the user to be logged in.

For example:

@login_required
def photos():
    ...

This prevents users who are not logged in from directly accessing protected pages.

## 3. Authorization

Authentication answers:
"Who is the user?"
Authorization answers:
"Is this user allowed to access this particular resource?"

SecureSnap checks the user's purchase record before allowing a photo to be downloaded.

This means that even if a user knows the URL of another photograph,
they cannot download it unless they have purchased it.

## 4. CSRF Protection
Cross-Site Request Forgery (CSRF) protection is enabled using Flask-WTF.
POST forms contain CSRF tokens so that requests cannot simply be submitted from another website without the required security token.
CSRF protection is applied to actions such as:

-Registration
-Login
-Photo purchase

## 5. Brute-Force Protection
Repeated login attempts can be used to guess passwords.
To reduce this risk, Flask-Limiter is used to limit login attempts.

The current login limit is:
'5 attempts per minute'

When the limit is exceeded, the application returns:
'429 Too Many Requests'
This was tested manually by making multiple incorrect login attempts.

## 6. Input Validation
The registration system performs basic input validation.
It checks that:

Username is provided
Password is provided
Username is not too long
Password contains at least 8 characters
Username is not already registered
This prevents invalid or obviously weak input from being accepted.

## 7. SQL Injection Protection

The application uses SQLAlchemy for database operations instead of building SQL queries directly from user input.
For example:
User.query.filter_by(username=username).first() 
This allows the database library to handle user input as data rather
than treating it as part of an SQL statement.

I also tested the login page using the following SQL injection payload:

' OR '1'='1

The application returned:
Invalid username or password.
The login was not bypassed.
Result: PASS ✅

## 8. XSS Protection

Cross-Site Scripting (XSS) was also tested.
The following payload was entered as a username:
<script>alert('XSS')</script>
The JavaScript was not executed by the application.

Jinja2's default HTML escaping also helps prevent user-supplied HTML from being interpreted as executable content when rendered
through the templates.

Result: PASS ✅

## 9. Secure Download Authorization
The download route performs an authorization check before returning the image.

The application checks:

1.Is the user logged in?
2.Does the requested photo exist?
3.Has the current user purchased the photo?
If the purchase does not exist, the request is rejected.

Example response:
Access denied. You must purchase this photo first.

with HTTP status:
403 Forbidden

## 10. Security Logging

SecureSnap records important security-related events in:
security.log
Some of the events recorded include:
-Successful login
-Failed login
-User registration
-Logout
-Photo purchase
-Unauthorized download attempt
-Authorized download
-Duplicate purchase attempt
The application does not record user passwords in the log.

Example:
EVENT=SUCCESSFUL_LOGIN | USER=testuser2 | IP=127.0.0.1

This provides a basic way of monitoring security-related activity during the application's operation.

## 11. Security Testing

After implementing the security features, I tested the application against several common scenarios.

| Test | What I Tried | Expected Result | Result |
|---|---|---|---|
| SQL Injection | SQL injection login payload | Login should fail | PASS |
| Unauthorized Download | Download without purchasing | Access should be denied | PASS |
| Protected Page | Access `/photos` without login | Redirect to login | PASS |
| Brute Force | Multiple login attempts | Rate limit should trigger | PASS |
| XSS | JavaScript payload as username | Script should not execute | PASS |
| CSRF Protection | POST request without valid CSRF token | Request should be rejected | IMPLEMENTED |
---
# SQL Injection Test
Payload
' OR '1'='1

Result
The application returned:
"Invalid username or password."

The attacker was not logged in.
Result: PASS ✅
---
# Unauthorized Download Test

I logged into the application and attempted to access the download endpoint for a photo that had not been purchased.
The application returned:
Access denied. You must purchase this photo first.

The request was rejected with:
403 Forbidden

Result: PASS ✅
---
# Protected Page Test

I logged out and manually tried to access:
/photos

The application redirected me to the login page instead of showing the photo store. 

Result: PASS ✅
----
# Brute-Force Test

I intentionally entered an incorrect password multiple times on the login page.

After five attempts within the configured time period, the application displayed:

Too Many Requests
5 per 1 minute

The server returned HTTP status:
429

Result: PASS ✅
---
# XSS Test

I entered:

<script>alert('XSS')</script>

as a username during registration.

The browser did not execute the JavaScript.

Result: PASS ✅
---
## System Architecture

```text
                         User
                           │
                           ▼
                   ┌───────────────┐
                   │  Flask Web App │
                   └───────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        Authentication  Authorization  Input Security
              │            │            │
              ▼            ▼            ▼
         Flask-Login   Purchase Check   CSRF
         Password Hash Download Check   Validation
              │
              ▼
         ┌───────────────┐
         │ SQLite        │
         │ Database      │
         └───────────────┘
                 Security Monitoring
                         │
                         ▼
                 ┌───────────────┐
                 │ security.log  │
                 └───────────────┘
```

# Technologies Used
## Technologies Used

### Backend
- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- Flask-Limiter

### Database
- SQLite

### Frontend
- HTML
- CSS
- Jinja2 Templates

# 14. Project Structure

```text
SecureSnap/
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── photos.html
│   └── photo_detail.html
│
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

The following local files/folders are intentionally excluded from the Git repository:

```text
venv/
instance/
security.log
.env
```

# Running the Project
1. Clone the repository
git clone https://github.com/ms9520685-crypt/SecureSnap.git
cd SecureSnap

2. Create a virtual environment
python -m venv venv

3. Activate the virtual environment
On Windows:
venv\Scripts\activate

4. Install the required packages
pip install -r requirements.txt

5. Run the application
python app.py

Then open:
http://127.0.0.1:5000

# Configuration

The Flask secret key is read from an environment variable:

`SECRET_KEY`

For local development, the application has a fallback development key so that it can run without additional configuration.

For a real deployment, a strong secret key should be provided through an environment variable instead of keeping it in the source code.

# Current Limitations

SecureSnap is a student/portfolio cybersecurity project rather than a production e-commerce system.
Some parts would need additional work before being used in a real
production environment.

For example:

The sample photographs currently use external image URLs.
The application uses SQLite for simplicity.
The payment system is simulated rather than connected to a real
payment gateway.
The current security logging system is basic.
The development server should not be used for production.
HTTPS should be used in a real deployment.
A production application would need stronger secret management.

# Future Improvements

Some features I would like to add in the future include:

Admin dashboard
Role-based access control
Private cloud/local image storage
Real payment gateway integration
Email verification
Password reset
Security monitoring dashboard
Automated security testing
Better security headers
Docker deployment
Production database

# What I Learned

Through this project, I got practical experience with how different security mechanisms work together inside a web application.

The main things I worked with were:

Secure password storage
Authentication and sessions
Authorization and access control
CSRF protection
Rate limiting
Input validation
SQL injection prevention
XSS prevention
Security logging
Security testing

One of the main things I learned from the project is that simply having a login system is not enough to make a web application secure.
Different layers of protection are needed for different types of attacks and unauthorized access.

# Project

Project Name: SecureSnap: A cybersecurity Framework for Online Stock Photo E-commerce Platform
Type: Cybersecurity / Web Application
Backend: Python + Flask
Database: SQLite
Focus: Web Application Security
