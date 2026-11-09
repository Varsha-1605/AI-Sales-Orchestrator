// Backend address used by every page. Change it here when the API is hosted elsewhere.
const API_URL = 'http://localhost:8000';
const WS_URL = API_URL.replace(/^http/, 'ws');

// The backend gives each session a secret token. Send it with every API request
// (needed when the backend runs with AUTH_ENABLED=true).
const nativeFetch = window.fetch.bind(window);
window.fetch = (url, options = {}) => {
    const token = localStorage.getItem('session_token');
    if (token && String(url).startsWith(API_URL)) {
        options = {...options, headers: {...(options.headers || {}), 'X-Session-Token': token}};
    }
    return nativeFetch(url, options);
};

// WebSocket address for a session, with the token as a query parameter
function socketUrl(sessionId) {
    const token = encodeURIComponent(localStorage.getItem('session_token') || '');
    return `${WS_URL}/ws/${sessionId}?token=${token}`;
}

// The backend prices the cart (offers, loyalty points, final price). Pages show its figures
// instead of working out discounts themselves, so every page and the payment agree.
let cartPricing = null;

async function refreshPricing() {
    try {
        const sessionId = localStorage.getItem('session_id');
        const response = await fetch(`${API_URL}/api/cart/${sessionId}`);
        if (response.ok) cartPricing = (await response.json()).pricing;
    } catch (error) {
        console.error('Could not load the cart price:', error);
    }
    return cartPricing;
}

// What the customer will pay. Falls back to the given amount when the backend price is not loaded
function payableTotal(fallbackAmount) {
    return cartPricing ? Math.round(cartPricing.final_price) : fallbackAmount;
}

// Short text for the offer, for example '10% OFF'. Empty when there is no offer
function offerBadgeText() {
    if (!cartPricing || !cartPricing.original_price || !cartPricing.discount_amount) return '';
    return `${Math.round(cartPricing.discount_amount / cartPricing.original_price * 100)}% OFF`;
}

// Product photos available in frontend/images, by catalog id. Products without a photo get a plain placeholder.
const PRODUCT_IMAGES = {
    VH001: 'images/classic blue formal shirt.png',
    VH002: 'images/white premium shirt.jpg',
    VH003: 'images/light pink shirt.png',
    VH004: 'images/navy blue tie.jpg',
    VH005B: 'images/stripped tie.jpg',
    VH006: 'images/brown belt.jpg'
};

const PRODUCT_IMAGE_PLACEHOLDER = 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="500" viewBox="0 0 400 500">' +
    '<rect width="400" height="500" fill="#E7E2D8"/>' +
    '<path d="M150 190l50-30 50 30 40 20-20 40-20-10v120H150V240l-20 10-20-40z" fill="none" stroke="#55616A" stroke-width="4" stroke-linejoin="round"/>' +
    '</svg>');

function productImage(productId) {
    return PRODUCT_IMAGES[productId] || PRODUCT_IMAGE_PLACEHOLDER;
}

// Lines that explain the price: items, subtotal, the offer, loyalty points and what the customer pays.
// Without them a cart total that is lower than the item prices looks like a mistake.
function cartSummaryText(subtotal, itemCount) {
    const lines = [`Items: ${itemCount}`, `Subtotal: ₹${subtotal.toLocaleString()}`];
    if (cartPricing) {
        if (cartPricing.discount_amount > 0) {
            lines.push(`${cartPricing.offers[0]}: -₹${Math.round(cartPricing.discount_amount).toLocaleString()}`);
        }
        if (cartPricing.points_used > 0) {
            lines.push(`Loyalty points: -₹${Math.round(cartPricing.points_used).toLocaleString()}`);
        } else if (cartPricing.points_usable > 0) {
            lines.push(`Loyalty points you can use: ₹${Math.round(cartPricing.points_usable).toLocaleString()}`);
        }
    }
    lines.push(`Total to pay: ₹${payableTotal(subtotal).toLocaleString()}`);
    return lines.join('\n');
}

// Said once, the moment the cart earns an offer, for example "Multi-buy: 10% off on 2+ items".
let lastOfferShown = '';
function newOfferText() {
    const offer = cartPricing && cartPricing.offers.length ? cartPricing.offers[0] : '';
    const changed = offer !== lastOfferShown;
    lastOfferShown = offer;
    return changed && offer ? `${offer} has been applied to your cart.` : '';
}

// What one more item would earn, from the backend, for example "Add 1 more item to get 20% off."
function nextOfferText() {
    const next = cartPricing && cartPricing.next_offer;
    if (!next) return '';
    return `Add ${next.items_needed} more ${next.items_needed === 1 ? 'item' : 'items'} to get ${next.discount_percent}% off your cart.`;
}

// Loyalty points are only used when the customer chooses to. True while they could still use some.
function pointsAreAvailable() {
    return Boolean(cartPricing && cartPricing.points_usable > 0 && !cartPricing.use_points);
}

async function setUsePoints(use) {
    try {
        const sessionId = localStorage.getItem('session_id');
        const response = await fetch(`${API_URL}/api/cart/points?session_id=${encodeURIComponent(sessionId)}&use=${use}`, {method: 'POST'});
        if (response.ok) cartPricing = (await response.json()).pricing;
    } catch (error) {
        console.error('Could not change the loyalty points choice:', error);
    }
}

// Which products are in stock somewhere, loaded once. Until it loads every product counts as available.
let productAvailability = null;

async function loadAvailability() {
    try {
        const response = await fetch(`${API_URL}/api/products/availability`);
        if (response.ok) productAvailability = (await response.json()).availability;
    } catch (error) {
        console.error('Could not load the stock:', error);
    }
}

function isInStock(productId) {
    return !productAvailability || productAvailability[productId] !== false;
}

// The backend refused an item that is out of stock: take it back out of this page's cart copy
function undoLocalAdd(productId) {
    const line = cartItems.find(item => item.id === productId);
    if (!line) return;
    if ((line.quantity || 1) > 1) {
        line.quantity -= 1;
    } else {
        cartItems = cartItems.filter(item => item.id !== productId);
    }
    localStorage.setItem('cartItems', JSON.stringify(cartItems));
}
