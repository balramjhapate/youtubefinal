<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('video_downloads', function (Blueprint $table) {
            $table->string('final_video_path')->nullable()->after('synthesized_audio_path');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('video_downloads', function (Blueprint $table) {
            $table->dropColumn('final_video_path');
        });
    }
};
