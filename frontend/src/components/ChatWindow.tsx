import React, { useEffect, useRef } from "react";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import KakaoMapView from "./KakaoMapView";
import ExamplePrompts from "./ExamplePrompts";
import TypingIndicator from "./TypingIndicator";

interface Props {
  messages: Message[];
  onPromptClick: (prompt: string) => void;
  isLoading: boolean;
  typingText?: string;
}

const ChatWindow: React.FC<Props> = ({ messages, onPromptClick, isLoading, typingText }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // 메시지가 추가될 때마다 스크롤을 맨 아래로 이동
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div 
      ref={scrollRef}
      className="w-full max-w-full flex flex-col gap-3 h-[65vh] overflow-y-auto p-6 bg-white/70 rounded-2xl shadow-lg border border-green-100 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
    >
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <ExamplePrompts onPromptClick={onPromptClick} />
        </div>
      ) : (
        <>
          {messages.map((msg, i) => (
            <div key={i}>
              {msg.type === "map" ? (
                <>
                  {/* map 타입: 텍스트 + 지도 보기 버튼 + 지도 */}
                  <MessageBubble 
                    role={msg.role} 
                    content={msg.content} 
                    link={msg.link} // 👈 link prop 전달
                  />
                  {msg.data && <KakaoMapView data={msg.data} />}
                </>
              ) : (
                /* text 타입: 텍스트만 */
                <MessageBubble role={msg.role} content={msg.content} />
              )}
            </div>
          ))}
          
          {/* 로딩 중일 때 TypingIndicator 표시 */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] p-3 rounded-2xl bg-gray-100 border border-gray-200 rounded-bl-none shadow-sm">
                <TypingIndicator text={typingText ?? "생각 정리 중.."} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ChatWindow;
