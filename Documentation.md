# Milestone 3: Database Queries and RESTful API Development Report

## OddCity - Virtual Casino Gaming Platform

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Database Choice and Design](#2-database-choice-and-design)
3. [Programming Language and Framework](#3-programming-language-and-framework)
4. [RESTful API Endpoints](#4-restful-api-endpoints)
5. [Complex Queries Implementation](#5-complex-queries-implementation)
6. [Authentication System](#6-authentication-system)
7. [User Roles and Authorization](#7-user-roles-and-authorization)
8. [Security Features](#8-security-features)
9. [API Testing Guide](#9-api-testing-guide)
10. [Swagger API Documentation](#10-swagger-api-documentation)

---

## 1. Project Overview

OddCity is a virtual casino gaming platform that allows users to play various casino games including Coinflip, Roulette, and Blackjack using virtual currency. The system features a complete user management system, wallet functionality, dynamic game rules managed by administrators, and comprehensive game statistics tracking.

### Key Features:
- **User Registration and Authentication**: Session-based authentication with CSRF protection
- **Virtual Wallet System**: Deposit, withdraw, and balance management
- **Three Casino Games**: Coinflip, Roulette, and Blackjack
- **Admin Dashboard**: User management, game statistics, and rule configuration
- **Dynamic Rule System**: Administrators can modify payout rates in real-time

---

## 2. Database Choice and Design

### 2.1 Database Management System

We chose **MySQL** as our relational database management system. MySQL was selected for the following reasons:
- Excellent support for transactions (ACID compliance)
- Strong data integrity through foreign key constraints
- Wide ecosystem support and documentation
- Compatibility with Python's `mysql-connector` library


Database Setup Instructions:

- Before running the project, please make sure your MySQL server is running
- Start your MySQL server (e.g., via XAMPP, WAMP, MAMP, or MySQL Workbench)
- Create a database named game_db
- Update the database connection settings according to your local environment

**Connection Configuration** (`game_api/config.py`):

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'game_db'
}
```
Make sure to replace the user and password fields with your own MySQL credentials if they differ from the default values.

### 2.2 Database Schema

The database consists of **9 main tables** with proper relationships:

#### Tables and Their Purposes:

| Table | Purpose |
|-------|---------|
| `users` | Stores user accounts with email, password hash, status, and admin flag |
| `wallets` | Manages virtual currency balances for each user |
| `rule_sets` | Contains game rule configurations (house edge, payout multipliers) |
| `rules` | Individual rules within each rule set |
| `games` | Records all game sessions with type, status, and results |
| `bets` | Tracks individual bets placed in games |
| `payouts` | Records win/loss outcomes for each bet |
| `transactions` | Logs deposit and withdrawal operations |
| `logs` | Audit trail for user actions (login, logout) |

#### Entity-Relationship Diagram:

```
┌─────────────┐
│   users     │
│─────────────│
│ user_id (PK)│
│ email       │
│ password    │
│ is_admin    │
│ status      │
└──────┬──────┘
       │
       │ 1:N
       ├─────────────────────────────────────┐
       │                                     │
┌──────▼──────┐                    ┌─────────▼─────────┐
│  wallets    │                    │   rule_sets       │
│─────────────│                    │───────────────────│
│ wallet_id   │                    │ rule_set_id (PK)  │
│ user_id (FK)│                    │ name              │
│ balance     │                    │ house_edge        │
│ currency    │                    │ is_active         │
└──────┬──────┘                    │ created_by (FK)   │
       │ 1:N                               │ 1:N
       │                                   │
┌──────▼──────────┐              ┌─────────▼─────────┐
│ transactions    │              │     rules         │
│─────────────────│              │───────────────────│
│ tx_id (PK)      │              │ rule_id (PK)      │
│ user_id (FK)    │              │ rule_set_id (FK)  │
│ wallet_id (FK)  │              │ rule_type         │
│ tx_type         │              │ rule_param        │
└─────────────────┘              └───────────────────┘

┌──────────────┐
│   games      │
│──────────────│
│ game_id (PK) │
│ user_id (FK) │──────────────────────────┐
│ rule_set_id  │                          │
│ game_type    │                          │
│ game_result  │                          │
│ status       │                          │
└──────┬───────┘                          │
       │ 1:N                              │
       │                                  │
┌──────▼──────────┐                       │
│     bets        │                       │
│─────────────────│                       │
│ bet_id (PK)     │                       │
│ game_id (FK)    │                       │
│ user_id (FK)    │───────────────────────┘
│ bet_type        │
│ bet_value       │
│ stake_amount    │
└──────┬──────────┘
       │ 1:1
       │
┌──────▼──────────┐
│    payouts      │
│─────────────────│
│ payout_id (PK)  │
│ bet_id (FK)     │
│ win_amount      │
│ outcome         │
└─────────────────┘
```

### 2.3 Relationship Details

#### 1. **users** → **wallets** (1:1)
- Each user has exactly one wallet
- `wallets.user_id` → `users.user_id`

#### 2. **users** → **rule_sets** (1:N)
- Admin users can create multiple rule sets
- `rule_sets.created_by_admin_id` → `users.user_id`

#### 3. **rule_sets** → **rules** (1:N)
- A rule set can contain multiple rules (payout configurations)
- `rules.rule_set_id` → `rule_sets.rule_set_id`

#### 4. **users** → **games** (1:N)
- A user can play multiple games
- `games.user_id` → `users.user_id`

#### 5. **rule_sets** → **games** (1:N)
- A rule set can be used in multiple games
- `games.rule_set_id` → `rule_sets.rule_set_id`

#### 6. **games** → **bets** (1:N)
- A game can have multiple bets (currently 1:1, designed for future multi-bet support)
- `bets.game_id` → `games.game_id`

#### 7. **bets** → **payouts** (1:1)
- Each bet has exactly one payout record (win or loss)
- `payouts.bet_id` → `bets.bet_id` (UNIQUE)

#### 8. **wallets** → **transactions** (1:N)
- A wallet can have multiple transactions (deposits/withdrawals)
- `transactions.wallet_id` → `wallets.wallet_id`

#### 9. **users** → **logs** (1:N)
- A user can have multiple log entries (login/logout actions)
- `logs.user_id` → `users.user_id`

### 2.4 Data Flow Examples

#### Example 1: Coinflip Game Flow

```
1. User places a bet
   └─> games: INSERT (game_id=1, user_id=5, rule_set_id=1, game_type='coinflip', status='ACTIVE')

2. Bet is recorded
   └─> bets: INSERT (bet_id=1, game_id=1, user_id=5, bet_type='choice', bet_value='yazi', stake_amount=10)

3. Wallet balance is deducted
   └─> wallets: UPDATE balance = balance - 10 WHERE user_id=5

4. Game result is determined
   └─> games: UPDATE game_result='{"result":"yazi","is_win":true}', status='COMPLETED'

5. If WIN: Payout is created and balance updated
   └─> payouts: INSERT (bet_id=1, win_amount=19.50, outcome='WIN')
   └─> wallets: UPDATE balance = balance + 19.50 WHERE user_id=5

6. If LOSS: Only payout record is created
   └─> payouts: INSERT (bet_id=1, win_amount=0, outcome='LOSS')
```

#### Example 2: Wallet Deposit Flow

```
1. User requests deposit
   └─> wallets: SELECT balance FROM wallets WHERE user_id=5 FOR UPDATE (row lock)

2. Balance is updated
   └─> wallets: UPDATE balance = balance + 100 WHERE user_id=5

3. Transaction is logged
   └─> transactions: INSERT (user_id=5, wallet_id=1, amount=100, tx_type='DEPOSIT')
```

#### Example 3: Admin Rule Set Change

```
1. Admin creates new rule set
   └─> rule_sets: INSERT (name='High Payout', house_edge=3.0, is_active=FALSE)

2. Admin adds rules to the set
   └─> rules: INSERT (rule_set_id=2, rule_type='coinflip_payout', rule_param='1.98')

3. Admin activates the new rule set
   └─> rule_sets: UPDATE is_active=FALSE WHERE is_active=TRUE (deactivate old)
   └─> rule_sets: UPDATE is_active=TRUE WHERE rule_set_id=2 (activate new)

4. New games use the new rule set
   └─> games: INSERT (..., rule_set_id=2, ...)
   └─> Payout calculated using new rules from rule_set_id=2
```

### 2.5 Raw SQL - No ORM Used

As required, we implemented all database operations using **raw SQL queries** without any ORM. All queries are written manually using the `mysql-connector-python` library.

**Example from `game_api/database.py`**:
```python
def get_db_connection():
    try:
        conn = mysql.connector.connect(**Config.DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None
```

### 2.6 Database Indexes for Performance

We created indexes on frequently queried columns to optimize performance:

```sql
-- Games table indexes
CREATE INDEX idx_games_user_id ON games(user_id);
CREATE INDEX idx_games_rule_set_id ON games(rule_set_id);
CREATE INDEX idx_games_game_type ON games(game_type);
CREATE INDEX idx_games_started_at ON games(started_at);
CREATE INDEX idx_games_status ON games(status);

-- Bets table indexes
CREATE INDEX idx_bets_game_id ON bets(game_id);
CREATE INDEX idx_bets_user_id ON bets(user_id);

-- Payouts table indexes
CREATE INDEX idx_payouts_outcome ON payouts(outcome);

-- Transactions table indexes
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
```

---

## 3. Programming Language and Framework

### 3.1 Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.x |
| **Web Framework** | Flask |
| **Database Connector** | mysql-connector-python |
| **Session Management** | Flask-Session (filesystem-based) |
| **CORS Support** | Flask-CORS |
| **Rate Limiting** | Flask-Limiter |
| **Password Hashing** | Werkzeug Security |

### 3.2 Project Structure

```
OddCity/
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── game_api/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection & schema
│   ├── auth.py              # Authentication endpoints
│   ├── wallet.py            # Wallet operations
│   ├── coinflip.py          # Coinflip game logic
│   ├── roulette.py          # Roulette game logic
│   ├── blackjack.py         # Blackjack game logic
│   ├── rules.py             # Rule management (Admin)
│   ├── admin.py             # Admin dashboard APIs
│   ├── services/
│   │   ├── game_service.py  # Game business logic
│   │   └── wallet_service.py # Wallet business logic
│   └── utils/
│       ├── csrf.py          # CSRF protection
│       ├── validators.py    # Input validation
│       └── logger.py        # Logging utilities
├── frontend/                 # User interface
└── admin_frontend/          # Admin panel interface
```

### 3.3 Application Factory Pattern

The Flask application uses the factory pattern for initialization (`game_api/__init__.py`):

```python
from flask import Flask
from flask_session import Session
from flask_cors import CORS
from flask_limiter import Limiter

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True)
    Session(app)
    limiter.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(rules_bp)
    app.register_blueprint(coinflip_bp)
    app.register_blueprint(roulette_bp)
    app.register_blueprint(blackjack_bp)
    app.register_blueprint(admin_bp)

    # Initialize database
    init_db()

    return app
```

---

## 4. RESTful API Endpoints

All API endpoints follow RESTful conventions with appropriate HTTP methods (GET, POST, PUT, DELETE).

### 4.1 Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register` | Create new user account | No |
| POST | `/login` | Authenticate user | No |
| POST | `/logout` | End user session | Yes + CSRF |
| GET | `/me` | Get current user info | Yes |
| GET | `/me/games` | Get user's game history | Yes |
| GET | `/me/stats` | Get user's statistics | Yes |
| PUT | `/me/password` | Change password | Yes + CSRF |
| GET | `/csrf-token` | Get CSRF token | Yes |

### 4.2 Wallet Endpoints (CRUD Operations)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/wallets/me` | **READ** - Get wallet balance | Yes |
| POST | `/wallets/me/deposit` | **CREATE** - Deposit funds | Yes + CSRF |
| POST | `/wallets/me/withdraw` | **UPDATE** - Withdraw funds | Yes + CSRF |

### 4.3 Game Endpoints

#### Coinflip Game
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/game/coinflip/play` | Play coinflip game | Yes + CSRF |

#### Roulette Game
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/game/roulette/play` | Play roulette game | Yes + CSRF |

#### Blackjack Game
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/game/blackjack/active` | Check for active game | Yes |
| POST | `/game/blackjack/start` | **CREATE** - Start new game | Yes + CSRF |
| POST | `/game/blackjack/hit` | Draw a card | Yes + CSRF |
| POST | `/game/blackjack/stand` | End turn | Yes + CSRF |
| POST | `/game/blackjack/resume` | Resume active game | Yes + CSRF |

### 4.4 Admin Endpoints (Full CRUD)

**Note:** All POST, PUT, and DELETE operations require CSRF token for security.

#### User Management
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/users` | **READ** - List all users | Admin |
| POST | `/admin/user/<id>/ban` | **UPDATE** - Ban user | Admin + CSRF |
| POST | `/admin/user/<id>/unban` | **UPDATE** - Unban user | Admin + CSRF |
| GET | `/admin/user/<id>/history` | **READ** - Get user transactions | Admin |
| GET | `/admin/user/<id>/games` | **READ** - Get user's games | Admin |

#### Rule Set Management (Full CRUD)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/rule-sets` | **READ** - List all rule sets | Admin |
| POST | `/admin/rule-sets` | **CREATE** - Create new rule set | Admin + CSRF |
| GET | `/admin/rule-sets/<id>` | **READ** - Get rule set details | Admin |
| POST | `/admin/rule-sets/<id>/activate` | **UPDATE** - Activate rule set | Admin + CSRF |
| POST | `/admin/rule-sets/<id>/deactivate` | **UPDATE** - Deactivate rule set | Admin + CSRF |
| DELETE | `/admin/rule-sets/<id>` | **DELETE** - Delete rule set | Admin + CSRF |

#### Individual Rule Management (Full CRUD)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/admin/rule-sets/<id>/rules` | **CREATE** - Add rule | Admin + CSRF |
| PUT | `/admin/rules/<id>` | **UPDATE** - Modify rule | Admin + CSRF |
| DELETE | `/admin/rules/<id>` | **DELETE** - Remove rule | Admin + CSRF |
| GET | `/admin/rule-types` | **READ** - List available rule types | Admin |

#### Dashboard Statistics
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/dashboard/stats` | Platform statistics | Admin |
| GET | `/admin/dashboard/recent-games` | Recent game activity | Admin |
| GET | `/admin/dashboard/top-players` | Top players leaderboard | Admin |

---

## 5. Complex Queries Implementation

### 5.1 Nested Query - Dashboard Statistics

This complex query aggregates data from multiple tables using JOINs and subqueries:

```sql
SELECT
    COUNT(DISTINCT g.game_id) as total_games,
    COUNT(DISTINCT g.user_id) as unique_players,
    COALESCE(SUM(b.stake_amount), 0) as total_bets,
    COALESCE(SUM(p.win_amount), 0) as total_payouts,
    SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END) as total_wins,
    SUM(CASE WHEN p.outcome = 'LOSS' THEN 1 ELSE 0 END) as total_losses
FROM games g
LEFT JOIN bets b ON b.game_id = g.game_id
LEFT JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.status = 'COMPLETED'
AND g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
```

**Location**: `game_api/admin.py` - `dashboard_stats()` function

### 5.2 Nested Query - Top Winners Calculation

This query calculates net profit using nested aggregations:

```sql
SELECT
    u.user_id,
    u.email,
    COALESCE(SUM(p.win_amount), 0) as total_winnings,
    COALESCE(SUM(b.stake_amount), 0) as total_bets,
    (COALESCE(SUM(p.win_amount), 0) - COALESCE(SUM(b.stake_amount), 0)) as net_profit
FROM users u
JOIN games g ON g.user_id = u.user_id
LEFT JOIN bets b ON b.game_id = g.game_id
LEFT JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
GROUP BY u.user_id
ORDER BY net_profit DESC
LIMIT %s
```

**Location**: `game_api/admin.py` - `top_players()` function

### 5.3 Nested Query - Active Rule Value Retrieval

This query retrieves rule values by joining rule_sets and rules tables:

```sql
SELECT r.rule_param
FROM rules r
JOIN rule_sets rs ON r.rule_set_id = rs.rule_set_id
WHERE rs.is_active = TRUE AND r.rule_type = %s
LIMIT 1
```

**Location**: `game_api/rules.py` - `get_active_rule_value()` function

### 5.4 Complex Query - User Game History with Statistics

```sql
SELECT
    g.game_id,
    g.game_type,
    g.game_result,
    g.started_at,
    g.ended_at,
    g.status,
    rs.name as rule_set_name,
    b.bet_type,
    b.bet_value,
    b.stake_amount,
    p.win_amount,
    p.outcome
FROM games g
LEFT JOIN rule_sets rs ON g.rule_set_id = rs.rule_set_id
LEFT JOIN bets b ON b.game_id = g.game_id
LEFT JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.user_id = %s
ORDER BY g.started_at DESC
LIMIT %s OFFSET %s
```

**Location**: `game_api/services/game_service.py` - `get_user_games()` method

### 5.5 Complex Query - Game Statistics Aggregation

```sql
SELECT
    COUNT(DISTINCT g.game_id) as total_games,
    COALESCE(SUM(b.stake_amount), 0) as total_bets,
    COALESCE(SUM(p.win_amount), 0) as total_payouts,
    SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END) as win_count,
    SUM(CASE WHEN p.outcome = 'LOSS' THEN 1 ELSE 0 END) as loss_count
FROM games g
LEFT JOIN bets b ON b.game_id = g.game_id
LEFT JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.status = 'COMPLETED'
AND g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
AND g.user_id = %s
AND g.game_type = %s
```

**Location**: `game_api/services/game_service.py` - `get_game_stats()` method

### 5.6 Recent Games with Full Details

```sql
SELECT
    g.game_id,
    g.game_type,
    g.game_result,
    g.started_at,
    g.ended_at,
    u.email as player_email,
    rs.name as rule_set_name,
    b.stake_amount,
    p.win_amount,
    p.outcome
FROM games g
JOIN users u ON g.user_id = u.user_id
LEFT JOIN rule_sets rs ON g.rule_set_id = rs.rule_set_id
LEFT JOIN bets b ON b.game_id = g.game_id
LEFT JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.status = 'COMPLETED'
ORDER BY g.started_at DESC
LIMIT %s
```

**Location**: `game_api/admin.py` - `recent_games()` function

---

## 6. Authentication System

### 6.1 Session-Based Authentication

We implemented **session-based authentication** using Flask-Session with filesystem storage:

**Configuration** (`game_api/config.py`):
```python
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = 'flask_session_cache'
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

### 6.2 Password Security

Passwords are hashed using **Werkzeug's security module** with PBKDF2:

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Registration
hashed_password = generate_password_hash(password)

# Login verification
if check_password_hash(user['password_hash'], password):
    # Login successful
```

### 6.3 Login Endpoint Implementation

**POST `/login`** (`game_api/auth.py`):

```python
@auth_bp.route('/login', methods=['POST'])
@get_limiter().limit("10 per minute")  # Brute force protection
def login_user():
    data = request.get_json()
    email = data['email']
    password = data['password']

    cursor.execute("""
        SELECT user_id, email, password_hash, is_admin, status
        FROM users WHERE email = %s
    """, (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password_hash'], password):
        if user['status'] == 'BANNED':
            return jsonify({'message': 'Account is banned'}), 403

        session['user_id'] = user['user_id']
        session['email'] = user['email']
        session['is_admin'] = user['is_admin']

        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401
```

### 6.4 Registration Endpoint Implementation

**POST `/register`** (`game_api/auth.py`):

```python
@auth_bp.route('/register', methods=['POST'])
@get_limiter().limit("5 per hour")  # Spam protection
def register_user():
    # Validate input
    is_valid, error = validate_email(email)
    is_valid, error = validate_password(password)

    # Hash password and create user
    hashed_password = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
        (email, hashed_password)
    )
    new_user_id = cursor.lastrowid

    # Create wallet for user
    cursor.execute(
        "INSERT INTO wallets (user_id) VALUES (%s)",
        (new_user_id,)
    )

    return jsonify({'user_id': new_user_id}), 201
```

### 6.5 Protected Routes Decorator

```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

---

## 7. User Roles and Authorization

### 7.1 Role Definition

The system has two user roles:

| Role | Description | Permissions |
|------|-------------|-------------|
| **Regular User** | Standard player | Play games, manage wallet, view own history |
| **Admin** | Administrator | All user permissions + user management, rule configuration, platform statistics |

### 7.2 Admin Detection

Admin status is stored in the `users` table as a boolean flag:

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(200) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    is_admin BOOLEAN DEFAULT FALSE,  -- Admin flag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.3 Admin Required Decorator

```python
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'message': 'Admin access required!'}), 403
        return f(*args, **kwargs)
    return decorated_function
```

### 7.4 Usage Example

```python
@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    # Only admins can access this endpoint
    cursor.execute("""
        SELECT u.user_id, u.email, u.status, u.is_admin, w.balance
        FROM users u
        LEFT JOIN wallets w ON u.user_id = w.user_id
        ORDER BY u.created_at DESC
    """)
    return jsonify(cursor.fetchall())
```

### 7.5 Default Admin Account

A default admin account is created during database initialization:

```python
def create_default_admin(conn, cursor):
    admin_email = 'admin@example.com'
    admin_password = 'admin'
    hashed_password = generate_password_hash(admin_password)

    cursor.execute("""
        INSERT INTO users (email, password_hash, is_admin, status)
        VALUES (%s, %s, TRUE, 'ACTIVE')
    """, (admin_email, hashed_password))
```

---

## 8. Security Features

### 8.1 CSRF Protection

All state-changing operations require a CSRF token:

**Token Generation** (`game_api/utils/csrf.py`):
```python
def generate_csrf_token():
    token = secrets.token_hex(32)
    session['_csrf_token'] = token
    session['_csrf_timestamp'] = datetime.utcnow().isoformat()
    return token
```

**CSRF Decorator**:
```python
def csrf_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-CSRF-Token')

        if not validate_csrf_token(token):
            return jsonify({'error': 'Invalid CSRF token'}), 403

        return f(*args, **kwargs)
    return decorated_function
```

### 8.2 Rate Limiting

We use Flask-Limiter to prevent abuse:

```python
# Global limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Per-endpoint limits
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Brute force protection
def login_user():
    ...

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")  # Spam protection
def register_user():
    ...
```

### 8.3 Input Validation

All user inputs are validated before processing:

```python
def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    return True, None

def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    return True, None
```

### 8.4 SQL Injection Prevention

All queries use parameterized statements:

```python
# Safe: Using parameterized query
cursor.execute(
    "SELECT * FROM users WHERE email = %s",
    (email,)  # Parameter passed separately
)

# Never: String concatenation
# cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")  # VULNERABLE!
```

### 8.5 Row-Level Locking for Race Conditions

Database transactions use `FOR UPDATE` to prevent race conditions:

```python
# Lock wallet row during transaction
cursor.execute(
    "SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE",
    (user_id,)
)
wallet = cursor.fetchone()

# Now safely update
cursor.execute(
    "UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s",
    (amount, wallet_id)
)
```

### 8.6 Cookie Security

```python
SESSION_COOKIE_HTTPONLY = True   # Prevents XSS access to cookies
SESSION_COOKIE_SAMESITE = 'Lax' # CSRF protection
SESSION_COOKIE_SECURE = True    # HTTPS only (in production)
```

---

## 9. API Testing Guide

### 9.1 Setup Instructions

#### ⚠️ IMPORTANT SETUP REQUIREMENTS

**WARNING:** Before running the server, you must set up the database properly.

1. **Start MySQL Server**
   - Make sure MySQL server is running on your system

2. **Create Database**
   - Open MySQL command line or any MySQL script executor
   - Run the following command to create the required database:
   ```sql
   CREATE DATABASE game_db;
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Flask Server**
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:3001`

### 9.2 Database Configuration

The application connects to MySQL with these settings (`game_api/config.py`):

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'game_db'
}
```

**Note:** Make sure your MySQL credentials match the configuration. The database schema and default data will be created automatically when the Flask application starts.

---

## 10. Swagger API Documentation

For detailed API testing and interactive documentation, we provide a **Swagger UI** interface.

### 10.1 Accessing Swagger UI

Once the Flask server is running, you can access the Swagger API documentation at:

```
http://localhost:3001/apidocs/
```

### 10.2 How to Use Swagger UI

#### Step 1: Start the Server
Make sure the Flask server is running:
```bash
python run.py
```

#### Step 2: Open Swagger UI
Navigate to `http://localhost:3001/apidocs/` in your web browser.

#### Step 3: Explore Endpoints
The Swagger UI organizes all endpoints into categories:
- **Authentication** - Login, Register, Logout, CSRF Token
- **User** - Profile, Game History, Statistics, Password Change
- **Wallet** - Balance, Deposit, Withdraw
- **Games** - Coinflip, Roulette, Blackjack
- **Admin** - User Management, Dashboard Statistics
- **Admin Rules** - Rule Set and Rule Management

#### Step 4: Test an Endpoint
1. Click on any endpoint to expand it
2. View the endpoint description, parameters, and response schemas
3. Click **"Try it out"** button
4. Fill in the required parameters
5. Click **"Execute"** to send the request
6. View the response in the Response section

### 10.3 Authentication in Swagger

Since the API uses session-based authentication:

1. **First, login** using the `POST /login` endpoint with valid credentials
2. The session cookie will be automatically stored in your browser
3. **Get CSRF Token** using `GET /csrf-token` endpoint
4. For POST/PUT/DELETE requests, include the CSRF token in the `X-CSRF-Token` header

### 10.4 CSRF Token Usage

For all state-changing operations (POST, PUT, DELETE), you need to include the CSRF token:

**Option A: Via Header**
- Add header: `X-CSRF-Token: your_token_value`

**Option B: Via Request Body**
- Include in JSON: `{"csrf_token": "your_token_value", ...}`

### 10.5 Swagger Features

| Feature | Description |
|---------|-------------|
| **Interactive Testing** | Execute API calls directly from the browser |
| **Request/Response Examples** | View sample request bodies and response formats |
| **Parameter Documentation** | See required and optional parameters for each endpoint |
| **Schema Definitions** | Understand the structure of request and response objects |
| **Authentication Info** | See which endpoints require authentication or admin access |

### 10.6 Default Test Credentials

For testing purposes, you can use the default admin account:

| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `admin` |

---

## Summary

This project implements a complete RESTful API for a virtual casino platform with:

- ✅ **MySQL Database** with 9 normalized tables
- ✅ **Raw SQL Queries** (no ORM used)
- ✅ **Complex Nested Queries** for statistics and reporting
- ✅ **Full CRUD Operations** on all major entities
- ✅ **Session-Based Authentication** with secure password hashing
- ✅ **User Roles** (Regular User and Admin)
- ✅ **CSRF Protection** for all state-changing operations
- ✅ **Rate Limiting** to prevent abuse
- ✅ **Transaction Support** with row-level locking

The API follows RESTful conventions and can be tested using Postman or curl as demonstrated in the testing guide.

