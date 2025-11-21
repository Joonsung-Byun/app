import React, {useEffect, useState} from "react";
import { marked } from "marked";
import type { MessageRole } from "../types";

interface Props {
  role: MessageRole;
  content: string;
  link?: string;
}

const MessageBubble: React.FC<Props> = ({ role, content, link }) => {
  const [htmlContent, setHtmlContent] = useState<string>('');

  useEffect(() => {
    const processContent = async () => {
      // 마크다운을 HTML로 변환하고 모든 a태그에 target="_blank" 추가
      const parsed = await marked.parse(content);
      const processed = parsed.replace(
        /<a /g, 
        '<a target="_blank" rel="noopener noreferrer" '
      );
      setHtmlContent(processed);
    };
    
    processContent();
  }, [content]);

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
            ? "bg-transparent text-gray-700 "
            : isUser
            ? "bg-green-200 text-gray-800 rounded-br-none shadow-sm"
            : "bg-gray-100 text-gray-700 border border-gray-200 rounded-bl-none shadow-sm"
        }`}
      >
        {/* 마크다운 HTML 렌더링 */}
        <div 
          className="ai_answer prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5"
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        />
        
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