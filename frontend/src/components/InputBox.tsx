import React from "react";
import type { FormEvent } from "react";

interface Props {
  message: string;
  setMessage: (value: string) => void;
  onSend: (message: string) => void;
  variant?: "hero" | "chat";
  isSending?: boolean;
}

const InputBox: React.FC<Props> = ({
  message,
  setMessage,
  onSend,
  variant = "chat",
  isSending = false,
}) => {
  const isEmpty = !message.trim();
  const isDisabled = isEmpty || isSending;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isDisabled) return;
    onSend(message);
    setMessage("");
  };

  const baseClass =
    "flex gap-3 bg-white border rounded-xl p-3 transition shadow-sm";
  const heroClass = "border-[#e0d6c7] shadow-md";
  const chatClass = "border-gray-200";

  return (
    <form
      onSubmit={handleSubmit}
      className={`${baseClass} ${variant === "hero" ? heroClass : chatClass}`}
    >
      <input
        type="text"
        placeholder="어디로 나들이 가고 싶으신가요?"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="flex-1 text-gray-700 px-3 py-2 focus:ring-2 focus:ring-green-400 focus:outline-none rounded-lg bg-transparent"
      />
      <button
        type="submit"
        disabled={isDisabled}
        className={`flex justify-center items-center gap-1 text-white font-medium px-4 rounded-lg transition ${
          isDisabled
            ? "bg-[#fcc5ae] cursor-not-allowed"
            : "bg-[#ec9676] hover:bg-[#d58769] hover:cursor-pointer"
        }`}
      >
        <span className="sr-only">보내기</span> 
        <svg
				  xmlns="http://www.w3.org/2000/svg"
				  width="16"
				  height="16"
				  viewBox="0 0 24 24"
				  fill="none"
				  stroke="currentColor"
				  stroke-width="2"
				  stroke-linecap="round"
				  stroke-linejoin="round"
				>
				  <line x1="22" y1="2" x2="11" y2="13" />
				  <polygon points="22 2 15 22 11 13 2 9 22 2" />
				</svg>
      </button>
    </form>
  );
};

export default InputBox;
