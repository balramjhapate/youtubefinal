<?php

use Illuminate\Support\Facades\Route;
use Inertia\Inertia;
use Laravel\Fortify\Features;

Route::get('/', function () {
    return Inertia::render('welcome', [
        'canRegister' => Features::enabled(Features::registration()),
    ]);
})->name('home');

Route::middleware(['auth', 'verified'])->group(function () {
    Route::get('dashboard', function () {
        return Inertia::render('dashboard');
    })->name('dashboard');
});

// Video routes - No authentication required for local-only project
Route::get('/videos', [\App\Http\Controllers\VideoController::class, 'index'])->name('videos.index');
Route::get('/videos/extract', function () {
    return \Inertia\Inertia::render('Videos/Extract');
})->name('videos.extract');
Route::post('/videos/extract', [\App\Http\Controllers\VideoController::class, 'extract'])->name('videos.extract.post');
Route::get('/videos/{video}', [\App\Http\Controllers\VideoController::class, 'show'])->name('videos.show');
Route::post('/videos/{video}/download', [\App\Http\Controllers\VideoController::class, 'download'])
    ->name('videos.download');
Route::post('/videos/{video}/transcribe', [\App\Http\Controllers\VideoController::class, 'transcribe'])
    ->name('videos.transcribe');
Route::post('/videos/{video}/process-ai', [\App\Http\Controllers\VideoController::class, 'processAI'])
    ->name('videos.process-ai');

require __DIR__.'/settings.php';
