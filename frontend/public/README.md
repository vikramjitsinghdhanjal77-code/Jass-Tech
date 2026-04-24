# JASS TECHNOLOGIES Hardware - Static Website

A clean, responsive HTML/CSS website for selling computer hardware components.

## 🚀 Features

- **User Login** - Username/password authentication with HTML5 validation
- **Product Listing** - Browse hardware components with search and filters
- **Shopping Cart** - Add items and view order summary
- **Checkout** - Complete order with Cash on Delivery payment option
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## 📁 Files

- `index.html` - Home page with hero section and featured products
- `login.html` - User login page with form validation
- `products.html` - Product listing with search and category filters
- `cart.html` - Shopping cart with order summary
- `checkout.html` - Checkout form with shipping and payment details
- `style.css` - Complete styling for all pages

## 🎨 Design

- **Color Scheme**: Blue (#1e3a8a, #2563eb) with Orange accents (#f97316)
- **Typography**: Segoe UI, system fonts
- **Layout**: Modern, clean, minimalist design
- **Components**: Cards, forms, buttons with hover effects

## 🛠️ Technical Details

- **Pure HTML/CSS** - No JavaScript required
- **HTML5 Forms** - Built-in validation
- **Semantic HTML** - Proper structure and accessibility
- **CSS Gradients** - Modern visual effects
- **Responsive Grid** - Adapts to all screen sizes

## 🔧 How to Run

### Option 1: Python Simple Server
```bash
cd /app/frontend/public
python3 -m http.server 8080
```
Then open: http://localhost:8080/index.html

### Option 2: Any Web Server
Simply serve the files from any web server. All pages are static HTML.

## 📱 Pages Overview

### Home Page (index.html)
- Hero section with call-to-action
- Why Choose JASS TECHNOLOGIES features
- Popular products showcase
- Footer with quick links

### Login Page (login.html)
- Username and password fields
- HTML5 form validation
- Remember me checkbox
- Redirects to products page on submit

### Products Page (products.html)
- Search bar with autocomplete
- Category filter (GPU, CPU, RAM, etc.)
- Sort options (price, popularity)
- 6 hardware components with:
  - Product image placeholder
  - Specifications
  - Price
  - Add to Cart button

### Cart Page (cart.html)
- 3 sample items pre-loaded
- Quantity selector
- Remove item button
- Order summary sidebar with:
  - Subtotal
  - Free shipping
  - Tax calculation
  - Total amount
- Proceed to Checkout button

### Checkout Page (checkout.html)
- Shipping information form
- Cash on Delivery payment option
- Order notes textarea
- Terms & conditions checkbox
- Order summary sidebar
- Place Order button shows success modal

## 🎯 Form Validations

All forms use HTML5 validation:
- **Username**: Min 3 characters, alphanumeric
- **Password**: Min 6 characters
- **Email**: Valid email format
- **Phone**: 10 digits
- **ZIP Code**: 5-6 digits
- **Required Fields**: Marked with *

## 💡 Notes

- Cart items are static (pre-populated for demo)
- No actual backend or database
- All navigation works via HTML links
- Forms redirect using method="get"
- Success modal shows on checkout submit

## 🎨 Customization

To customize colors, edit `style.css`:
- Primary blue: `#1e3a8a`, `#2563eb`
- Accent orange: `#f97316`
- Background: `#f7fafc`
- Text: `#1a202c`

## 📊 Browser Support

Works on all modern browsers:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## 📄 License

Educational/Demo purposes - JASS TECHNOLOGIES Hardware Website 2025
