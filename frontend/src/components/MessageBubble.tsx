import React, {useEffect} from "react";
import type { MessageRole } from "../types";

interface Props {
  role: MessageRole;
  content: string;
  link?: string; // 👈 선택적 link prop 추가
}

const MessageBubble: React.FC<Props> = ({ role, content, link }) => {
  useEffect(() => {
    if (link)
    console.log("MessageBubble rendered with link:", link);
  }, [link]);
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed ${
          link 
            ? "bg-transparent text-gray-700 " // link가 있으면 배경 투명 box shadow 제거
            : isUser
            ? "bg-green-200 text-gray-800 rounded-br-none shadow-sm"
            : "bg-gray-100 text-gray-700 border border-gray-200 rounded-bl-none shadow-sm"
        }`}
      >
        {content}
        
        {/* link가 있으면 "지도 보기" 버튼 표시 */}
        {link && (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-2 px-4 py-2 bg-yellow-400 text-gray-800 rounded-lg hover:bg-yellow-500 transition-colors text-sm font-medium"
          >
            📍 지도 보기
          </a>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;