import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import { useChatStorage } from "../hooks/useChatStorage";
import type { Message } from "../types";

const ChatPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
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

  // HeroPage에서 전달된 초기 메시지 처리
  useEffect(() => {
    const initialMessage = location.state?.initialMessage;
    if (initialMessage) {
      handleSend(initialMessage);
      // state 클리어
      navigate("/chat", { replace: true, state: {} });
    }
  }, []);

  const handlePromptClick = (prompt: string) => {
    setMessage(prompt);
  };

  const handleSend = async (userMessage: string) => {
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
        // 🟢 [수정] 데이터가 배열인지 확인하고, 단일 객체(지오코딩 결과)라면 배열로 감싸주기
        // RAG 검색 결과는 배열([...])로 오고, 지오코딩 결과는 단일 객체({...})로 올 수 있음
        let mapData = data.data;
        
        if (!Array.isArray(mapData)) {
            // 지오코딩 툴 결과가 address 필드를 가지고 있다면 desc로 매핑 (지도 UI 호환성)
            if (mapData.address && !mapData.desc) {
                mapData.desc = mapData.address;
            }
            mapData = [mapData]; // 배열로 변환
        }

        // 지도 응답 메시지 생성
        const mapMsg: Message = {
          role: "ai",
          type: "map",
          content: data.content || "위치를 지도에 표시해 드려요! 📍", // 내용이 비어있을 경우 기본 멘트
          link: data.link,
          data: mapData, // 항상 배열 형태로 저장됨
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

  window.addEventListener("beforeunload", () => {
    localStorage.removeItem("chatMessages");
    // conversation_id 삭제 후 새로 생성
    const uuid = crypto.randomUUID();
    localStorage.setItem("conversation_id", uuid);
  });

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 bg-linear-to-b from-green-50 via-white to-green-50">
      <div className="w-full max-w-4xl">
        <div className="flex justify-center items-center gap-5 mb-3">
          <img src="/logo2_copy.webp" alt="" className="w-36 md:w-52 h-auto block"/>
          <h1 className="text-xl font-bold">키즈 액티비티 가이드🍃</h1>
        </div>

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
