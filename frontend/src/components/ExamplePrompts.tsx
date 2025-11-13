import React from "react";

interface Props {
  onPromptClick: (text: string) => void;
}

const prompts = [
  "🌳 주말에 아이랑 갈만한 부산 공원 추천",
  "🎨 비 오는 날 서울 실내 체험장 알려줘",
  "🚴 성수동 근처 자전거 탈 수 있는 곳",
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
