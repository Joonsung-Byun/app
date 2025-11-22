import React from "react";
import type { FormEvent } from "react";

interface Props {
  message: string;
  setMessage: (value: string) => void;
  onSend: (message: string) => void;
  variant?: "hero" | "chat";
}

const InputBox: React.FC<Props> = ({ message, setMessage, onSend, variant = "chat" }) => {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
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
        className="bg-[#e79f85] text-white font-medium px-5 rounded-lg hover:bg-[#d58769] transition hover:cursor-pointer"
      >
        보내기
      </button>
    </form>
  );
};

export default InputBox;
