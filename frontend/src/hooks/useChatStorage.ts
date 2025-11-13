import { useState, useEffect } from "react";
import type { Message } from "../types";

export function useChatStorage() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem("chatMessages");
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const clearMessages = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");

    // localStorage에 chatMessages에 AI의 환영인사는 넣어두기
    const welcomeMessage: Message = {
      role: "ai",
      content: "안녕하세요! 아이와 함께할 수 있는 나들이 장소를 추천해드릴게요!",
      type: "text",
    };
    setMessages([welcomeMessage]);
  };

  return { messages, addMessage, clearMessages };
}
