<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return redirect()->route('dashboard');
})->name('home');

// Dashboard route - No authentication required for local-only project
Route::get('dashboard', [\App\Http\Controllers\DashboardController::class, 'index'])->name('dashboard');

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
Route::post('/videos/{video}/synthesize', [\App\Http\Controllers\VideoController::class, 'synthesize'])
    ->name('videos.synthesize');
Route::post('/videos/{video}/process-final', [\App\Http\Controllers\VideoController::class, 'processFinalVideo'])
    ->name('videos.process-final');

// Application Settings routes - No authentication required for local-only project
Route::get('/app-settings', [\App\Http\Controllers\SettingsController::class, 'index'])->name('settings.index');
Route::post('/app-settings', [\App\Http\Controllers\SettingsController::class, 'update'])->name('settings.update');
Route::post('/app-settings/create', [\App\Http\Controllers\SettingsController::class, 'store'])->name('settings.store');
Route::delete('/app-settings/{setting}', [\App\Http\Controllers\SettingsController::class, 'destroy'])->name('settings.destroy');

// Voice Cloning route - Placeholder for future feature
Route::get('/voice-cloning', function () {
    return \Inertia\Inertia::render('VoiceCloning/Index');
})->name('voice-cloning.index');

// Bulk operations routes
Route::post('/videos/bulk-delete', [\App\Http\Controllers\VideoController::class, 'bulkDelete'])
    ->name('videos.bulk-delete');
Route::post('/videos/bulk-process', [\App\Http\Controllers\VideoController::class, 'bulkProcess'])
    ->name('videos.bulk-process');

// Retry operations routes
Route::post('/videos/{video}/retry-transcription', [\App\Http\Controllers\VideoController::class, 'retryTranscription'])
    ->name('videos.retry-transcription');
Route::post('/videos/{video}/retry-ai', [\App\Http\Controllers\VideoController::class, 'retryAIProcessing'])
    ->name('videos.retry-ai');
Route::post('/videos/{video}/retry-tts', [\App\Http\Controllers\VideoController::class, 'retryTTS'])
    ->name('videos.retry-tts');
Route::post('/videos/{video}/retry-final', [\App\Http\Controllers\VideoController::class, 'retryFinalVideo'])
    ->name('videos.retry-final');
Route::post('/videos/{video}/reprocess', [\App\Http\Controllers\VideoController::class, 'reprocess'])
    ->name('videos.reprocess');
Route::delete('/videos/{video}', [\App\Http\Controllers\VideoController::class, 'destroy'])
    ->name('videos.destroy');

require __DIR__.'/settings.php';
