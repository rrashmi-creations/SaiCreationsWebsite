# Quick API checks

After deployment, open `https://YOUR-API/docs`.

1. `GET /health` should return status `ok`.
2. `GET /api/products` should return `[]` until you add products.
3. `GET /api/settings` should return default store settings.
4. Create the first admin via `POST /api/auth/setup`.
5. Log in via `POST /api/auth/login`, copy the access token and use the Authorize button in `/docs`.
6. Test product creation, update, list and delete.
7. Upload a product image from the storefront admin. Confirm its URL is a Cloudinary HTTPS URL.
8. Create a test order and confirm it appears in Admin > Orders.

Do not paste credentials or access tokens into screenshots, public issue trackers or repository files.
