import React, { useEffect, useState, useCallback, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import { useChatStorage } from "../hooks/useChatStorage";
import type { Message } from "../types";

const ChatPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const sendingRef = useRef(false);

  // localStorage에 conversation_id를 uuid로 저장
  useEffect(() => {
    const conversationId = localStorage.getItem("conversation_id");
    if (!conversationId) {
      const uuid = crypto.randomUUID();
      localStorage.setItem("conversation_id", uuid);
    }
  }, []);

  const { messages, addMessage, clearMessages } = useChatStorage();
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [typingText, setTypingText] = useState("요청 분석 중...");

  const handleSend = useCallback(
    async (userMessage: string) => {
      const trimmed = userMessage.trim();
      if (!trimmed) return;
      if (sendingRef.current) return;
      sendingRef.current = true;

      let statusSource: EventSource | null = null;

      const userMsg: Message = { role: "user", content: trimmed, type: "text" };
      addMessage(userMsg);
      setIsLoading(true);
      setTypingText("요청 분석 중..");

      try {
        const conversationId = localStorage.getItem("conversation_id") || "";

        // SSE로 진행 상태 스트리밍
        if (conversationId) {
          const url = `http://localhost:8080/api/chat/stream/${conversationId}`;
          statusSource = new EventSource(url);

          statusSource.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.status) {
                setTypingText(data.status);
              }
            } catch {
              // 파싱 에러는 무시
            }
          };

          statusSource.onerror = () => {
            statusSource?.close();
          };
        }

        // API 호출
        const response = await fetch("http://localhost:8080/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        body: JSON.stringify({
          message: trimmed,
          conversation_id: conversationId,
        }),
      });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.conversation_id) {
          localStorage.setItem("conversation_id", data.conversation_id);
        }

        if (data.type === "map") {
          const mapMsg: Message = {
            role: "ai",
            type: "map",
            content: "",
            link: data.link,
            data: data.data,
          };
          addMessage(mapMsg);
        } else {
          const textMsg: Message = {
            role: "ai",
            type: "text",
            content: data.content,
          };
          addMessage(textMsg);
        }
      } catch (error) {
        console.error("API 호출 오류:", error);

        const errorMsg: Message = {
          role: "ai",
          type: "text",
          content: "죄송해요, 일시적인 오류가 발생했어요. 다시 시도해주세요. 😢",
        };
        addMessage(errorMsg);
      } finally {
        if (statusSource) {
          statusSource.close();
        }
        setIsLoading(false);
        sendingRef.current = false;
      }
    },
    [addMessage]
  );

  // HeroPage에서 전달된 초기 메시지 처리
  useEffect(() => {
    const initialMessage = location.state?.initialMessage;
    if (initialMessage) {
      handleSend(initialMessage);
      // state 클리어
      navigate("/chat", { replace: true, state: {} });
    }
  }, [location.state, handleSend, navigate]);

  const handlePromptClick = (prompt: string) => {
    setMessage(prompt);
  };

  useEffect(() => {
    const handleBeforeUnload = () => {
      const uuid = crypto.randomUUID();
      localStorage.setItem("conversation_id", uuid);
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  return (
    <div className="min-h-screen flex justify-center px-4 pt-20 pb-6 md:pt-20 bg-linear-to-b from-green-50 via-white to-green-50">
      <div className="w-full max-w-6xl">
        <div className="mb-4 min-w-0">
          <ChatWindow
            messages={messages}
            onPromptClick={handlePromptClick}
            isLoading={isLoading}
            typingText={typingText}
          />
        </div>

        <InputBox variant="chat" message={message} setMessage={setMessage} onSend={handleSend} />
        <button
          onClick={() => {
            clearMessages();
          }}
          className="text-xs text-gray-400 mt-2 hover:underline block mx-auto"
        >
          대화 초기화
        </button>
      </div>
    </div>
  );
};

export default ChatPage;
