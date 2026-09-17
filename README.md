# DropTag — SEO keywords for images

Add title, keywords, and rating into image metadata. Download SEO-ready JPGs with clean file names.

## Easiest way (web app)

1. Double-click **`run_web.bat`**
2. Browser opens **DropTag** at http://127.0.0.1:7860
3. Drop images → fill title / keywords / rating → **Tag & download**

Keep the black window open while you use the app. Press Ctrl+C to stop.

## Folder / CLI way (optional)

1. Put photos in **`images`**
2. Edit **`keywords.txt`**
3. Double-click **`run.bat`**
4. Get tagged JPGs in **`output`**

## Check it worked (Windows)

Right-click the downloaded **`.jpg`** → **Properties → Details** → Title / Tags / Comments / Rating.

> Windows does not show Tags on PNG. DropTag always outputs JPG.

## Deploy on Vercel

The web app uses FastAPI, and Vercel can run it as a Python serverless function.

1. Push this folder to a GitHub repository.
2. In Vercel, choose **Add New Project** and import the repository.
3. Leave the framework preset as **Other** and deploy.
4. Open the Vercel URL and test with one small JPG first.

The `api/index.py` and `vercel.json` files are the Vercel adapter. Do not remove
`requirements.txt`; Vercel uses it to install Pillow and the metadata packages.

Vercel is suitable for small image batches. Serverless platforms have upload,
execution-time, and memory limits. If users need large images or many images at
once, host this FastAPI backend on Render, Railway, or another Python host and
keep the static frontend on Vercel.

### Connect checkout

The pricing buttons are prepared for hosted checkout links. Create one payment
link for the annual plan (€35/year) and one for the lifetime plan (€45 once) in
Stripe Payment Links, Lemon Squeezy, or a similar provider. Then paste the URLs
into `checkoutUrls.annual` and `checkoutUrls.lifetime` near the top of
`static/app.js`. The buttons will open the configured checkout in a new tab.
