import React from "react";

interface Props {
  onPromptClick: (text: string) => void;
}

const prompts = [
  "🌳 서울 공원 추천해줘",
  "🎨 12월 부산 행사 알려줘",
  "🚴 제주 해수욕장 추천해줘",
];

const ExamplePrompts: React.FC<Props> = ({ onPromptClick }) => {
  return (
    <div className="flex flex-wrap justify-center gap-3 animate-fadeIn">
      {prompts.map((text, i) => (
        <div
          key={i}
          onClick={() => onPromptClick(text)}
          className={`px-4 py-2 bg-white border border-green-200 shadow-sm rounded-full text-sm text-gray-700 select-none cursor-pointer hover:bg-green-50 transition 
            animate-floating delay-[${i * 300}ms]`}
        >
          {text}
        </div>
      ))}
    </div>
  );
};

export default ExamplePrompts;
