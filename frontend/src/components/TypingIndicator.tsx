'use client';

import { useState, useEffect } from 'react';

const MESSAGES = [
  '공공 장소를 찾는중..',
  '날씨 정보를 얻어오는 중..',
  '응답을 생성하는 중..',
];

export function TypingIndicator() {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    // messageIndex가 마지막(2)에 도달하면 더 이상 증가하지 않음
    if (messageIndex >= MESSAGES.length - 1) {
      return;
    }

    const interval = setInterval(() => {
      setMessageIndex((prev) => {
        if (prev >= MESSAGES.length - 1) {
          return prev; // 마지막 메시지에서 멈춤
        }
        return prev + 1;
      });
    }, 4000); // 4초마다 변경

    return () => clearInterval(interval);
  }, [messageIndex]);

  // 컴포넌트가 마운트될 때 초기화
  useEffect(() => {
    setMessageIndex(0);
  }, []);

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0s' }} />
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }} />
        <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.4s' }} />
      </div>
      <span className="text-sm text-gray-600">{MESSAGES[messageIndex]}</span>
    </div>
  );
}

export default TypingIndicator;
