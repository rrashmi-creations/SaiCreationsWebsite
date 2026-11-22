# Sai Creation — Cloud-backed storefront

This is an upgraded, cloud-backed version of the existing Sai Creation storefront. It retains the wine/pink design and replaces device-only product/settings storage with a shared FastAPI + Turso backend.

## Architecture

- **Frontend:** static HTML/CSS/JS in `frontend/`, hosted on GitHub Pages.
- **API:** FastAPI in `backend/`, hosted on Render.
- **Database:** Turso (libSQL / SQLite-compatible cloud database).
- **Product images:** Cloudinary.
- **Cart and wishlist:** intentionally remain in each visitor's browser. Product catalogue, store settings and orders are shared centrally.

## Before you start

Create accounts:
1. GitHub (you already have the repository).
2. Render: https://render.com/
3. Turso: https://turso.tech/
4. Cloudinary: https://cloudinary.com/

Do not put Turso tokens, Cloudinary API secrets, JWT secrets, setup keys or admin passwords in frontend files or GitHub.

## Step 1 — Create Turso database

From the Turso dashboard, create a database (for example `sai-creation-store`). Copy:
- Database URL (`libsql://...`)
- Database auth token

Keep both private. The backend creates its tables on first startup.

## Step 2 — Create Cloudinary account

From the Cloudinary dashboard, copy:
- Cloud name
- API key
- API secret

The API secret is backend-only. The frontend asks FastAPI for a short-lived signed upload request; images upload to Cloudinary and their HTTPS URLs are stored in Turso.

## Step 3 — Deploy FastAPI on Render

1. Upload this project's `backend/` folder to your GitHub repository.
2. In Render, choose **New > Blueprint** and select your repository. Render should detect the root-level `render.yaml` blueprint (it sets `rootDir: backend`).
3. Add the Turso and Cloudinary values in the Render Environment tab.
4. Confirm `JWT_SECRET` and `SETUP_SECRET` are generated as secret values. If not, generate strong random values yourself.
5. Deploy. Your API address will look like `https://sai-creation-api.onrender.com`.
6. Test `https://YOUR-API/health` — it should return `{"status":"ok",...}`.

If you deploy manually instead of Blueprint:
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add every variable from `backend/.env.example`.

**Free Render services can sleep when idle.** The first request after inactivity may take a little time. The database and images are not stored on Render's temporary disk.

## Step 4 — Configure the frontend

Edit `frontend/config.js` and replace the placeholder with your real Render URL:

```js
window.SAI_CONFIG = {
  API_BASE: "https://sai-creation-api.onrender.com"
};
```

Use your actual service hostname, without a trailing slash.

## Step 5 — Create the first admin account (one time)

After the API is deployed, use this one-time setup request. Replace the values; do not share the setup key publicly.

```bash
curl -X POST "https://YOUR-API/api/auth/setup" \
  -H "Content-Type: application/json" \
  -d '{"setup_secret":"YOUR_SETUP_SECRET","email":"YOUR_ADMIN_EMAIL","password":"A_LONG_UNIQUE_PASSWORD_12_CHARS_OR_MORE"}'
```

You can also send the same JSON using an API client such as Postman. The setup endpoint works only while there is no admin account. Once it succeeds, **remove `SETUP_SECRET` from Render's environment and redeploy**. Do not put the admin password in JavaScript or README.

Login from the website using the email and password you created.

## Step 6 — Publish GitHub Pages

1. Copy the contents of `frontend/` into the root of your existing repository (so `index.html` is at the repository root), or configure Pages to publish from the `/frontend` folder if your repository settings support that source.
2. In GitHub: **Settings > Pages**.
3. Select **Deploy from a branch**, branch `main`, folder `/ (root)` if you copied frontend to root.
4. Save and wait for deployment.
5. Open the Pages URL and test product loading.

For your existing repository, the Pages URL is commonly `https://rrashmi-creations.github.io/SaiCreationsWebsite/` if the repository is configured as a project site. Set `FRONTEND_ORIGINS` in Render to that exact origin: `https://rrashmi-creations.github.io` (origin excludes the repository path).

## Features included

- Public product catalogue, category filter, search and sorting.
- Admin login with server-side Argon2 password hashing and JWT sessions.
- Create, read, update and delete products.
- Cloudinary signed image upload.
- Global store settings and multiple WhatsApp department numbers.
- Public order enquiry creation; admin order list and status updates.
- Product/stock checks at order creation.
- Responsive storefront for mobile, tablet and desktop.

## API endpoints

| Method | Endpoint | Access |
|---|---|---|
| GET | `/health` | Public |
| GET | `/api/products` | Public |
| GET | `/api/products/{id}` | Public |
| GET | `/api/settings` | Public |
| POST | `/api/auth/setup` | One-time setup secret |
| POST | `/api/auth/login` | Public |
| POST | `/api/orders` | Public |
| POST | `/api/admin/products` | Admin |
| PUT | `/api/admin/products/{id}` | Admin |
| DELETE | `/api/admin/products/{id}` | Admin |
| PUT | `/api/admin/settings` | Admin |
| POST | `/api/admin/cloudinary-signature` | Admin |
| GET | `/api/admin/orders` | Admin |
| PATCH | `/api/admin/orders/{id}` | Admin |

Interactive API documentation is available at `https://YOUR-API/docs`.

## Important production notes

- This package is a deployment starter, not a claim that your external accounts have already been created or deployed. You must add your own service credentials and publish the files.
- Configure a backup/export process for Turso and Cloudinary. Free plans and quotas can change.
- Cloudinary's free allowance is quota-based; check its current limits and usage.
- Render's free instance may sleep. This affects response time, not the location of Turso/Cloudinary data.
- Public order creation here records an order enquiry and opens WhatsApp. It does **not** collect online payment, calculate shipping, send invoices, or automatically reserve/decrement inventory. Confirm those workflows before accepting paid orders.
- Add rate limiting, spam protection and stricter order validation before a high-volume public launch.
- Use HTTPS and a strong, unique admin password. Never commit `.env` files or API secrets.
- A fresh Turso database is seeded with the eight sample products from your existing storefront. Their image paths point to your existing repository `images/` folders; keep those folders when copying the frontend to the repository root. Existing products saved only in your old browser localStorage are not automatically migrated. Export/re-enter those products before switching live.
