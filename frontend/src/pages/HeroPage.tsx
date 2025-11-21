import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import InputBox from "../components/InputBox";
import ExamplePrompts from "../components/ExamplePrompts";

const HeroPage: React.FC = () => {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");

  const handlePromptClick = (prompt: string) => {
    setMessage(prompt);
  };

  const handleSend = async (userMessage: string) => {
    // /chat으로 이동하면서 메시지만 전달 (localStorage에는 저장하지 않음)
    navigate("/chat", { state: { initialMessage: userMessage } });
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 bg-linear-to-b from-green-50 via-white to-green-50">
      <div className="w-full max-w-4xl">
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
    </div>
  );
};

export default HeroPage;
