# Localization Implementation Plan

## Goal Description
Translate all Turkish text (comments, UI strings, API error messages, log messages) to English throughout the entire application to internationalize the codebase.

## User Review Required
> [!NOTE]
> This change affects user-facing text and API error responses. 

## Proposed Changes

### Backend (`game_api`)
Translate comments and API response strings (e.g., `'message': 'Veritabanı hatası'` -> `'message': 'Database error'`).

#### [MODIFY] [rules.py](file:///c:/Users/Emre/Documents/GitHub/OddCity/game_api/rules.py)
#### [MODIFY] [auth.py](file:///c:/Users/Emre/Documents/GitHub/OddCity/game_api/auth.py)
#### [MODIFY] [admin.py](file:///c:/Users/Emre/Documents/GitHub/OddCity/game_api/admin.py)
#### [MODIFY] [wallet.py](file:///c:/Users/Emre/Documents/GitHub/OddCity/game_api/wallet.py)
#### [MODIFY] [database.py](file:///c:/Users/Emre/Documents/GitHub/OddCity/game_api/database.py)
*And other python files as discovered during the pass.*

### Frontend (`frontend`)
Translate HTML text content and JavaScript dynamic strings.

#### [MODIFY] [index.html](file:///c:/Users/Emre/Documents/GitHub/OddCity/frontend/index.html)
#### [MODIFY] [script.js](file:///c:/Users/Emre/Documents/GitHub/OddCity/frontend/script.js)

### Admin Frontend (`admin_frontend`)
Translate Admin Panel UI and scripts.

#### [MODIFY] [index.html](file:///c:/Users/Emre/Documents/GitHub/OddCity/admin_frontend/index.html)
#### [MODIFY] [admin.js](file:///c:/Users/Emre/Documents/GitHub/OddCity/admin_frontend/admin.js)

## Verification Plan

### Manual Verification
1.  **Backend**: Check API responses for specific endpoints (e.g., try to login with wrong credentials and check if message is "Invalid credentials" instead of "Hatalı giriş").
2.  **Frontend**: Open the web page (if runnable) or inspect the HTML source to ensure visible text is English.
3.  **Admin**: Verify Admin panel text.

### Automated Verification
- I will run `grep` searches for common Turkish words (e.g., "Hata", "Giriş", "Kayıt", "Parola") after the changes to ensure nothing was missed.
