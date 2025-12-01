# Laravel + Inertia.js + React Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### Step 1: Install Laravel

**Option A: Using Laravel Installer (Recommended)**

First, install the Laravel installer globally (if not already installed):

```bash
composer global require laravel/installer
```

Then create a new Laravel project:

```bash
laravel new youtubefinal-laravel
cd youtubefinal-laravel
```

**Option B: Using Composer (Alternative)**

If you prefer not to use the Laravel installer:

```bash
composer create-project laravel/laravel youtubefinal-laravel
cd youtubefinal-laravel
```

> **Important**: When creating a Laravel 12 project, you'll be prompted to select a frontend provider (React, Vue, etc.) and other options. **Please handle these prompts yourself** - choose React as the frontend provider and configure other options as needed for your project.

> **Note**: The `laravel new` command creates a fresh Laravel installation with the latest stable version (Laravel 11+). Ensure you have PHP 8.2+ installed. If you need a specific Laravel version, you can use: `laravel new youtubefinal-laravel --version=11` or use Composer: `composer create-project laravel/laravel:^11.0 youtubefinal-laravel`

### Step 2: Install Laravel Breeze (Authentication - Optional)

**Note**: If you selected React and authentication options during project creation, you may already have authentication set up. If not, or if you want to use Laravel Breeze specifically:

Laravel Breeze provides a simple authentication scaffolding with React and Inertia.js:

```bash
composer require laravel/breeze --dev
php artisan breeze:install react
npm install
npm run build
php artisan migrate
```

> **Note**: If you already configured authentication during project creation, you can skip this step or use it to customize your authentication setup.

**What Breeze Installs:**

-   ✅ **Authentication System**: Login, Register, Password Reset, Email Verification
-   ✅ **React + Inertia.js Pages**: Pre-built authentication pages in React
-   ✅ **User Model & Migration**: Ready-to-use user authentication
-   ✅ **Middleware**: Authentication middleware configured
-   ✅ **Routes**: All authentication routes set up
-   ✅ **Layout Components**: Navigation, guest layout, authenticated layout

**Files Created by Breeze:**

-   `app/Http/Controllers/Auth/` - Authentication controllers
-   `resources/js/Pages/Auth/` - Login, Register, etc. pages
-   `resources/js/Components/` - Layout components
-   `routes/auth.php` - Authentication routes
-   `database/migrations/xxxx_create_users_table.php` - User migration

> **Note**: If you prefer a different stack, you can use: `php artisan breeze:install api` for API-only, or `php artisan breeze:install blade` for Blade templates. For this project, we use `react` since we're using React + Inertia.js.

### Step 3: Install Inertia.js (if not already installed by Breeze)

If Breeze didn't install Inertia.js or you need additional setup:

```bash
# Server-side
composer require inertiajs/inertia-laravel

# Client-side
npm install @inertiajs/react react react-dom
npm install -D @vitejs/plugin-react
```

```bash
# Server-side
composer require inertiajs/inertia-laravel

# Client-side
npm install @inertiajs/react react react-dom
npm install -D @vitejs/plugin-react
```

### Step 4: Setup Inertia.js (if needed)

**app/Http/Middleware/HandleInertiaRequests.php** (already exists, just update):

```php
<?php

namespace App\Http\Middleware;

use Illuminate\Http\Request;
use Inertia\Middleware;

class HandleInertiaRequests extends Middleware
{
    protected $rootView = 'app';

    public function share(Request $request): array
    {
        return array_merge(parent::share($request), [
            'auth' => [
                'user' => $request->user(),
            ],
        ]);
    }
}
```

**resources/js/app.jsx** (create this):

```jsx
import "./bootstrap";
import "../css/app.css";

import { createRoot } from "react-dom/client";
import { createInertiaApp } from "@inertiajs/react";
import { resolvePageComponent } from "laravel-vite-plugin/inertia-helpers";

createInertiaApp({
	title: (title) => `${title} - RedNote`,
	resolve: (name) =>
		resolvePageComponent(
			`./Pages/${name}.jsx`,
			import.meta.glob("./Pages/**/*.jsx")
		),
	setup({ el, App, props }) {
		const root = createRoot(el);
		root.render(<App {...props} />);
	},
});
```

**resources/views/app.blade.php** (create this):

```blade
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title inertia>{{ config('app.name', 'Laravel') }}</title>
    @routes
    @viteReactRefresh
    @vite(['resources/css/app.css', 'resources/js/app.jsx'])
    @inertiaHead
</head>
<body>
    @inertia
</body>
</html>
```

**vite.config.js** (update):

```javascript
import { defineConfig } from "vite";
import laravel from "laravel-vite-plugin";
import react from "@vitejs/plugin-react";

export default defineConfig({
	plugins: [
		laravel({
			input: "resources/js/app.jsx",
			refresh: true,
		}),
		react(),
	],
});
```

### Step 5: Create Your First Page

**resources/js/Pages/Home.jsx**:

```jsx
import { Head } from "@inertiajs/react";

export default function Home() {
	return (
		<>
			<Head title="Home" />
			<div className="container mx-auto px-4 py-8">
				<h1 className="text-3xl font-bold">Welcome to RedNote!</h1>
			</div>
		</>
	);
}
```

**routes/web.php**:

```php
<?php

use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::get('/', function () {
    return Inertia::render('Home');
});
```

### Step 6: Run the Application

```bash
# Terminal 1: Laravel
php artisan serve

# Terminal 2: Vite
npm run dev
```

Visit: http://localhost:8000

---

## 📁 Project Structure Overview

```
youtubefinal-laravel/
├── app/
│   ├── Http/
│   │   ├── Controllers/     # Your controllers
│   │   └── Middleware/      # Middleware
│   ├── Models/              # Eloquent models
│   ├── Services/            # Business logic
│   └── Jobs/                # Background jobs
├── resources/
│   ├── js/
│   │   ├── Pages/           # Inertia pages (React components)
│   │   ├── Components/      # Reusable React components
│   │   └── app.jsx          # Entry point
│   └── views/
│       └── app.blade.php    # Inertia root template
├── routes/
│   └── web.php              # Routes
└── database/
    └── migrations/          # Database migrations
```

---

## 🔑 Key Concepts

### 1. Inertia Pages (React Components)

Instead of API calls, you return React components directly from controllers:

```php
// Controller
return Inertia::render('Videos/Index', [
    'videos' => $videos,
]);
```

```jsx
// resources/js/Pages/Videos/Index.jsx
export default function Index({ videos }) {
	return <div>{/* Use videos prop directly */}</div>;
}
```

### 2. Form Submissions

Use Inertia's router instead of axios:

```jsx
import { router } from "@inertiajs/react";

// Instead of: axios.post('/videos', data)
router.post("/videos", data);
```

### 3. Navigation

```jsx
import { Link } from "@inertiajs/react";

// Instead of: <a href="/videos">
<Link href="/videos">Videos</Link>;
```

### 4. Redirects

```php
// Controller
return redirect()->route('videos.index')
    ->with('message', 'Video created!');
```

```jsx
// Access flash message
import { usePage } from "@inertiajs/react";

const { flash } = usePage().props;
{
	flash.message && <div>{flash.message}</div>;
}
```

---

## 🎯 Migration Path

1. **Start with Static Pages**: Dashboard, Settings (no API calls)
2. **Migrate List Pages**: Videos list (read-only)
3. **Add Forms**: Video extraction form
4. **Add Background Jobs**: Video processing
5. **Add Real-time Updates**: Polling or WebSockets

---

## 📦 Essential Packages

```bash
# HTTP Client
composer require guzzlehttp/guzzle

# Queue (for background jobs)
php artisan queue:table
php artisan migrate

# File Storage (already included)
# Just configure in config/filesystems.php
```

---

## 🔧 Common Tasks

### Create a Controller

```bash
php artisan make:controller VideoController
```

### Create a Model + Migration

```bash
php artisan make:model VideoDownload -m
```

### Create a Job

```bash
php artisan make:job ProcessVideo
```

### Run Migrations

```bash
php artisan migrate
```

### Run Queue Worker

```bash
php artisan queue:work
```

---

## 🎨 Styling

You can use Tailwind CSS (already included in Laravel):

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Or use any CSS framework you prefer (Bootstrap, Material-UI, etc.)

---

## 📚 Next Steps

1. Read the full migration guide: `LARAVEL_MIGRATION_GUIDE.md`
2. Set up your database
3. Create your first model and migration
4. Build your first Inertia page
5. Add background jobs for heavy processing

---

**Happy coding! 🚀**
