import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

interface PasswordInputProps extends React.ComponentProps<typeof Input> {
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function PasswordInput({
    value,
    onChange,
    ...props
}: PasswordInputProps) {
    const [showPassword, setShowPassword] = useState(false);

    return (
        <div className="relative">
            <Input
                type={showPassword ? 'text' : 'password'}
                value={value}
                onChange={onChange}
                className="pr-10"
                {...props}
            />
            <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full"
                onClick={() => setShowPassword(!showPassword)}
            >
                {showPassword ? (
                    <EyeOff className="size-4" />
                ) : (
                    <Eye className="size-4" />
                )}
            </Button>
        </div>
    );
}

