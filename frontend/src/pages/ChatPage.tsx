import React, { useEffect, useState } from "react";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import ExamplePrompts from "../components/ExamplePrompts";
import { useChatStorage } from "../hooks/useChatStorage";
import type { Message } from "../types";

const ChatPage: React.FC = () => {

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
  const [started, setStarted] = useState(messages.length > 0);
  const [isLoading, setIsLoading] = useState(false);

  const handlePromptClick = (prompt: string) => {
    setMessage(prompt);
  };

  const handleSend = async (userMessage: string) => {
    if (!started) setStarted(true);

    const userMsg: Message = { role: "user", content: userMessage, type: "text" };
    addMessage(userMsg);
    setIsLoading(true);

    try {
      // conversation_id 가져오기 (없으면 빈 문자열)
      const conversationId = localStorage.getItem("conversation_id") || "";

      // API 호출
      const response = await fetch("http://localhost:8080/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // 서버가 반환한 conversation_id 저장 (없으면 생성된 것)
      if (data.conversation_id) {
        localStorage.setItem("conversation_id", data.conversation_id);
      }

      // 응답 타입에 따라 처리
      if (data.type === "map") {
        // 지도 응답
        const mapMsg: Message = {
          role: "ai",
          type: "map",
          content: "",
          link: data.link,
          data: data.data,
        };
        addMessage(mapMsg);
      } else {
        // 텍스트 응답
        const textMsg: Message = {
          role: "ai",
          type: "text",
          content: data.content,
        };
        addMessage(textMsg);
      }
    } catch (error) {
      console.error("API 호출 오류:", error);
      
      // 에러 메시지 표시
      const errorMsg: Message = {
        role: "ai",
        type: "text",
        content: "죄송해요, 일시적인 오류가 발생했어요. 다시 시도해주세요. 😢",
      };
      addMessage(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  // 페이지 떠날 때 메시지만 삭제 (conversation_id는 유지)
  window.addEventListener("beforeunload", () => {
    localStorage.removeItem("chatMessages");
    // conversation_id는 유지!
  });

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-4xl">
        {started ? (
          <div className="flex justify-center items-center gap-5 mb-3">
            <img src="logo2_copy.webp" alt="" className="w-36 md:w-52 h-auto block"/>
            <h1 className="text-xl font-bold">키즈 액티비티 가이드🍃</h1>
          </div>
        ) : null}

        {/* Hero 화면 */}
        <div
          className={`transition-all duration-500 ease-in-out ${
            started
              ? "opacity-0 -translate-y-3 pointer-events-none h-0 overflow-hidden"
              : "opacity-100 translate-y-0"
          }`}
        >
          <div className="text-center mb-8">
            <div className="flex justify-center items-center mb-3">
              <img src="/logo_copy.webp" alt="" className="w-36 md:w-48 lg:w-72 h-auto block"/>
            </div>
            <p className="text-4xl md:text-5xl font-semibold text-[#3a3a35] mb-3 tracking-tight">
              아이와 주말 나들이 어때요?
            </p>
            <p className="text-sm text-[#9a9081]">
              지역·날씨·아이 연령에 맞는 장소를 챗봇이 추천해드릴게요.
            </p>
          </div>

          <div className="w-full">
            <InputBox
              variant="hero"
              message={message}
              setMessage={setMessage}
              onSend={handleSend}
            />
          </div>

          <div className="mt-6 flex justify-center">
            <ExamplePrompts onPromptClick={handlePromptClick} />
          </div>
        </div>

        {/* Chat 화면 */}
        <div
          className={`transition-all duration-500 ease-in-out ${
            started
              ? "opacity-100 translate-y-0"
              : "opacity-0 translate-y-3 pointer-events-none h-0 overflow-hidden"
          }`}
        >
          {started && (
            <>
              <div className="mb-4 min-w-0">
                <ChatWindow 
                  messages={messages} 
                  onPromptClick={handlePromptClick}
                  isLoading={isLoading}
                />
              </div>

              <InputBox
                variant="chat"
                message={message}
                setMessage={setMessage}
                onSend={handleSend}
              />
              <button
                onClick={clearMessages}
                className="text-xs text-gray-400 mt-2 hover:underline block mx-auto"
              >
                대화 초기화
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
