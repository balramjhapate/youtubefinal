import React from 'react';

export function Card({ children, className = '', ...props }) {
    return (
        <div
            className={`bg-white/5 border border-white/10 rounded-xl overflow-hidden ${className}`}
            {...props}
        >
            {children}
        </div>
    );
}
