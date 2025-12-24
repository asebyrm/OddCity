# OddCity API Documentation

This document provides examples for interacting with the OddCity Game API and Admin API.

## Base URL
- **All APIs**: `http://localhost:3001`

---

## Game API

### Authentication

#### Register
**POST** `/register`
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```
**Response (201 Created):**
```json
{
  "message": "Kullanıcı ve cüzdanı başarıyla oluşturuldu!",
  "user_id": 1
}
```

#### Login
**POST** `/login`
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```
**Response (200 OK):**
```json
{
  "message": "Giriş başarılı! Sunucu sizi hatırlayacak.",
  "is_admin": false
}
```
*Note: This sets a session cookie.*

#### Logout
**POST** `/logout`
*Requires Authentication*
**Response (200 OK):**
```json
{
  "message": "Başarıyla çıkış yapıldı."
}
```

### Wallet Operations

#### Get Wallet Info
**GET** `/wallets/me`
*Requires Authentication*
**Response (200 OK):**
```json
{
  "wallet": {
    "email": "user@example.com",
    "balance": 1000.0,
    "currency": "VIRTUAL",
    "updated_at": "Tue, 24 Dec 2024 12:00:00 GMT"
  }
}
```

#### Deposit
**POST** `/wallets/me/deposit`
*Requires Authentication*
```json
{
  "amount": 500
}
```
**Response (200 OK):**
```json
{
  "message": "Başarılı! 500.0 VIRTUAL cüzdanınıza eklendi.",
  "user": "user@example.com",
  "new_balance": 1500.0
}
```

#### Withdraw
**POST** `/wallets/me/withdraw`
*Requires Authentication*
```json
{
  "amount": 200
}
```
**Response (200 OK):**
```json
{
  "message": "Başarılı! 200.0 VIRTUAL cüzdanınızdan çekildi.",
  "user": "user@example.com",
  "new_balance": 1300.0
}
```

### Games

#### Coin Flip
**POST** `/game/play`
*Requires Authentication*
```json
{
  "amount": 100,
  "choice": "yazi" 
}
```
*Choice options: "yazi", "tura"*
**Response (Win):**
```json
{
  "message": "Tebrikler, KAZANDINIZ! (195.00)",
  "your_choice": "yazi",
  "result": "yazi",
  "new_balance": 1495.0
}
```

#### Roulette
**POST** `/game/roulette/play`
*Requires Authentication*
```json
{
  "amount": 50,
  "bet_type": "color",
  "bet_value": "red"
}
```
*Bet Types:*
- `number`: `bet_value` (0-36)
- `color`: `bet_value` ("red", "black")
- `parity`: `bet_value` ("odd", "even")

**Response:**
```json
{
  "message": "KAZANDINIZ!",
  "winning_number": 7,
  "winning_color": "red",
  "is_win": true,
  "payout": 100.0,
  "new_balance": 1595.0
}
```

#### Blackjack
**POST** `/game/blackjack/start`
*Requires Authentication*
```json
{
  "amount": 100
}
```
**Response:**
```json
{
  "player_hand": [{"suit": "H", "rank": "K"}, {"suit": "D", "rank": "5"}],
  "dealer_card": {"suit": "S", "rank": "10"},
  "player_value": 15,
  "status": "playing",
  "new_balance": 1495.0
}
```

**POST** `/game/blackjack/hit`
*Requires Authentication*
**Response:**
```json
{
  "player_hand": [...],
  "player_value": 18,
  "status": "playing"
}
```

**POST** `/game/blackjack/stand`
*Requires Authentication*
**Response:**
```json
{
  "player_hand": [...],
  "dealer_hand": [...],
  "player_value": 18,
  "dealer_value": 20,
  "status": "finished",
  "result": "lose",
  "message": "Krupiye Kazandı.",
  "payout": 0,
  "new_balance": 1495.0
}
```

---

## Admin API

### Authentication
*Uses the same `/login` endpoint. Requires `is_admin=True`.*

### User Management

#### List Users
**GET** `/admin/users`
*Requires Admin Authentication*
**Response (200 OK):**
```json
[
  {
    "user_id": 1,
    "email": "user@example.com",
    "status": "ACTIVE",
    "is_admin": 0,
    "created_at": "...",
    "balance": 1000.0,
    "currency": "VIRTUAL"
  },
  ...
]
```

#### Ban User
**POST** `/admin/user/<user_id>/ban`
*Requires Admin Authentication*
**Response (200 OK):**
```json
{
  "message": "Kullanıcı yasaklandı."
}
```

#### Unban User
**POST** `/admin/user/<user_id>/unban`
*Requires Admin Authentication*
**Response (200 OK):**
```json
{
  "message": "Kullanıcı yasağı kaldırıldı."
}
```

#### User History
**GET** `/admin/user/<user_id>/history`
*Requires Admin Authentication*
**Response (200 OK):**
```json
[
  {
    "transaction_id": 101,
    "amount": 100.0,
    "tx_type": "BET",
    "created_at": "..."
  },
  ...
]
```