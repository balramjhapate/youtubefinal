<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Setting extends Model
{
    protected $fillable = [
        'key',
        'value',
        'type',
        'group',
        'description',
    ];

    /**
     * Get the value attribute with proper type casting
     */
    public function getValueAttribute($value): mixed
    {
        $type = $this->attributes['type'] ?? 'string';

        return match ($type) {
            'json' => json_decode($value, true),
            'boolean' => filter_var($value, FILTER_VALIDATE_BOOLEAN),
            'integer' => (int) $value,
            default => $value,
        };
    }

    /**
     * Set the value attribute with proper type handling
     */
    public function setValueAttribute($value): void
    {
        $type = $this->attributes['type'] ?? 'string';

        $this->attributes['value'] = match ($type) {
            'json' => json_encode($value),
            'boolean' => $value ? '1' : '0',
            'integer' => (string) $value,
            default => (string) $value,
        };
    }

    /**
     * Get a setting value by key
     */
    public static function get(string $key, mixed $default = null): mixed
    {
        $setting = self::where('key', $key)->first();

        return $setting ? $setting->value : $default;
    }

    /**
     * Set a setting value by key
     */
    public static function set(string $key, mixed $value, string $type = 'string', string $group = 'general'): void
    {
        $setting = self::firstOrNew(['key' => $key]);
        $setting->value = is_array($value) ? json_encode($value) : $value;
        $setting->type = $type;
        $setting->group = $group;
        $setting->save();
    }

    /**
     * Get all settings by group
     */
    public static function getByGroup(string $group): array
    {
        return self::where('group', $group)
            ->get()
            ->mapWithKeys(fn ($setting) => [$setting->key => $setting->value])
            ->toArray();
    }
}
