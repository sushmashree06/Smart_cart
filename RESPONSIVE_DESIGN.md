# SmartCart Project Documentation

## Features & UI System

### 1. Fixed Header & Footer
- **Fixed Header (`.site-header`)**: Stays locked at the top (`z-index: 1000`) with a frosted glass backdrop filter.
- **Fixed Footer (`.site-footer`)**: Stays anchored at the bottom (`z-index: 999`).
- **Safe Content Padding (`.main-content`)**: Padded dynamically (`calc(var(--header-height) + 28px)` top and `calc(var(--footer-height) + 38px)` bottom) so content and actions are never clipped or hidden behind the header/footer on any screen.
- **Responsive Mobile Navigation**: Dropdown menu opens beneath the header on mobile screens with scrollable overflow.

### 2. SQLite Database (`smartcart.db`)
- Self-contained, zero-configuration database using Python's standard `sqlite3` library.
- Auto-initializes on startup with all 7 tables:
  - `admin` (with `profile_image`)
  - `users` (with `profile_image`)
  - `products` (with `admin_id`)
  - `customer_address`
  - `orders`
  - `order_items`
  - `password_resets`
- Pre-seeded with 8 sample products matching existing assets in `static/uploads/product_images/`.

### 3. Public Catalog & Storefront (`http://127.0.0.1:5000/`)
- Public visitors can immediately browse all products, view prices, categories, and descriptions without being blocked by a login screen.
- Login is only required for personalized actions (adding to cart, checkout, profile management, and order history).

### 4. Distinct Search & Filter Forms
- **Search Form (`.search-box-form`)**: Dedicated text search bar with search button and clear action.
- **Category Filter Form (`.filter-box-form`)**: Dedicated category selector with instant on-change filter and reset action.
- Both forms are individually styled, centered, and preserve each other's query parameters.

### 5. Standardized Profile Display & Uploads
- Dedicated user profile page: `templates/user/profile.html` (`/user/profile`).
- Fixed avatar size across admin and user profiles: `120px × 120px` circular avatar with clean fallback initials badge.
- Dedicated profile image serving routes:
  - User: `/uploads/user_profiles/<filename>`
  - Admin: `/uploads/admin_profiles/<filename>`

### 6. Admin Product Isolation
- Administrators only see, edit, update, filter, and delete their own products (`WHERE admin_id = ?`).
- One admin cannot access or manage another admin's inventory.

### 7. Cart & Proceed to Payment Flow
- Checkboxes pre-selected by default for instant and dynamic total calculation.
- "Select All" checkbox toggle.
- Quantity stepper controls (`+` and `-`).
- Prominent green **"Proceed to Payment →"** buttons on:
  - Shopping Cart page (`/user/cart`)
  - Floating cart notice banner on shop pages
  - Product details page (`/user/product/<id>`)
- Smart checkout routing (`/user/checkout`): navigates to address creation if needed, or straight to order confirmation and payment.

---

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to `http://127.0.0.1:5000/`
