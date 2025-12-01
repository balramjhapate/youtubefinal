<?php

namespace App\Http\Controllers;

use App\Models\Setting;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

class SettingsController extends Controller
{
    public function index(): Response
    {
        $settings = Setting::orderBy('group')->orderBy('key')->get()->groupBy('group');

        return Inertia::render('settings/Index', [
            'settings' => $settings->map(function ($group) {
                return $group->map(function ($setting) {
                    return [
                        'id' => $setting->id,
                        'key' => $setting->key,
                        'value' => $setting->value,
                        'type' => $setting->type,
                        'group' => $setting->group,
                        'description' => $setting->description,
                    ];
                });
            }),
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'settings' => 'required|array',
            'settings.*.key' => 'required|string',
            'settings.*.value' => 'nullable',
            'settings.*.type' => 'nullable|string',
        ]);

        foreach ($validated['settings'] as $settingData) {
            $setting = Setting::firstOrNew(['key' => $settingData['key']]);
            $setting->value = $settingData['value'] ?? '';
            $setting->type = $settingData['type'] ?? 'string';
            $setting->group = $settingData['group'] ?? 'general';
            $setting->save();
        }

        return back()->with('message', 'Settings updated successfully');
    }

    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'key' => 'required|string|unique:settings,key',
            'value' => 'nullable',
            'type' => 'nullable|string|in:string,json,boolean,integer',
            'group' => 'nullable|string',
            'description' => 'nullable|string',
        ]);

        Setting::create([
            'key' => $validated['key'],
            'value' => $validated['value'] ?? '',
            'type' => $validated['type'] ?? 'string',
            'group' => $validated['group'] ?? 'general',
            'description' => $validated['description'] ?? null,
        ]);

        return back()->with('message', 'Setting created successfully');
    }

    public function destroy(Setting $setting): RedirectResponse
    {
        $setting->delete();

        return back()->with('message', 'Setting deleted successfully');
    }
}
