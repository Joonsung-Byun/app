'use client';

interface TypingIndicatorProps {
  text: string;
}

export function TypingIndicator({ text }: TypingIndicatorProps) {

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0s' }} />
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }} />
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.4s' }} />
      </div>
      <span className="text-sm text-gray-600">{text}</span>
    </div>
  );
}

export default TypingIndicator;
