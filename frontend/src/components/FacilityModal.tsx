import React from "react";

export default function FacilityModal({
  facility,
  onClose,
  isProgramsLoading,
}: any) {
  if (!facility) return null;

  const {
    name,
    address,
    category1,
    category2,
    category3,
    programs = [],
    in_out,
  } = facility;


  const isSportsCategory = [category1, category2, category3].includes(
    "생활체육관"
  );

  const placeTypeColor =
    in_out === "실내"
      ? "bg-blue-100 text-blue-600"
      : in_out === "실외"
      ? "bg-green-100 text-green-600"
      : "bg-gray-100 text-gray-600";

  const catColor = "bg-purple-100 text-purple-600";

  // programs 배열 안에 실제로 보여줄 만한 내용이 있는지 체크
  const hasMeaningfulPrograms =
    Array.isArray(programs) &&
    programs.some((p: any) => {
      if (!p) return false;
      const hasNote =
        typeof p.note === "string" ? p.note.trim().length > 0 : !!p.note;
      const hasTime = !!p.time;
      const hasDay = !!p.day;
      const hasCost = !!p.cost;
      const hasAge =
        typeof p.age_min === "number" || typeof p.age_max === "number";

      return hasNote || hasTime || hasDay || hasCost || hasAge;
    });

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 px-4"
      onClick={handleOverlayClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto no-scrollbar p-6 animate-fadeIn">

        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">{name}</h2>
          <button
            className="text-gray-500 hover:text-black text-xl"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* Address */}
        <p className="text-gray-700 mb-3">{address}</p> 

        {/* Category Badges */}
        <div className="flex flex-wrap gap-2 mb-4">
          {category1 && (
            <span className={`${catColor} text-xs px-3 py-1 rounded-full`}>
              {category1}
            </span>
          )}
          {category2 && (
            <span className={`${catColor} text-xs px-3 py-1 rounded-full`}>
              {category2}
            </span>
          )}
          {category3 && (
            <span className={`${catColor} text-xs px-3 py-1 rounded-full`}>
              {category3}
            </span>
          )}

          {in_out && (
            <span className={`${placeTypeColor} text-xs px-3 py-1 rounded-full`}>
              {in_out}
            </span>
          )}
        </div>

        {/* Program / Note List */}
        <h3 className="font-semibold text-lg mb-3">
          {isSportsCategory ? "프로그램 목록" : "특이사항"}
        </h3>

        {isProgramsLoading ? (
          <div className="flex items-center justify-center py-6">
            <div className="w-6 h-6 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin mr-3" />
            <span className="text-gray-600 text-sm">
              정보를 불러오는 중이에요...
            </span>
          </div>
        ) : !hasMeaningfulPrograms ? (
          <div className="p-4 text-center text-gray-500">
            {isSportsCategory
              ? "등록된 프로그램 정보가 없어요."
              : "특이사항이 없어요. 카카오맵에서 더 자세한 정보를 확인해보세요!"}
          </div>
        ) : (
          programs
            .filter((p: any) => {
              if (!p) return false;
              const hasNote =
                typeof p.note === "string" ? p.note.trim().length > 0 : !!p.note;
              const hasTime = !!p.time;
              const hasDay = !!p.day;
              const hasCost = !!p.cost;
              const hasAge =
                typeof p.age_min === "number" || typeof p.age_max === "number";

              return hasNote || hasTime || hasDay || hasCost || hasAge;
            })
            .map((p: any, idx: number) => {
              const hasMin = typeof p.age_min === "number";
              const hasMax = typeof p.age_max === "number";

              let ageLabel = "";
              if (hasMin && hasMax) {
                if (p.age_max === 99) {
                  ageLabel = `${p.age_min}세 이상`;
                } else {
                  ageLabel = `${p.age_min} ~ ${p.age_max}세`;
                }
              } else if (hasMin) {
                ageLabel = `${p.age_min}세 이상`;
              } else if (hasMax) {
                ageLabel = `${p.age_max}세 이하`;
              }

              // 비용 표기 정규화
              let costLabel = "";
              if (p.cost !== null && p.cost !== undefined && p.cost !== "") {
                if (typeof p.cost === "number") {
                  costLabel = `${p.cost.toLocaleString()}원`;
                } else {
                  const trimmed = String(p.cost).trim();
                  const noSpace = trimmed.replace(/\s+/g, "");

                  if (noSpace === "입장금액있음") {
                    costLabel = "입장금액 있음";
                  } else if (noSpace === "입장금액없음") {
                    costLabel = "입장금액 없음";
                  } else {
                    const numeric = Number(trimmed.replace(/,/g, ""));
                    if (!Number.isNaN(numeric)) {
                      costLabel = `${numeric.toLocaleString()}원`;
                    } else {
                      costLabel = trimmed;
                    }
                  }
                }
              }

              return (
                <div
                  key={idx}
                  className="glass-card mb-3 p-4 text-sm text-gray-800"
                >
                  {/* Note (시설 설명/부가정보) */}
                  {p.note && (
                    <p className="mb-2 text-gray-900 font-medium text-[16px]">
                      {p.note}
                    </p>
                  )}

                  {/* Time */}
                  {p.time && (
                    <p className="text-gray-700">
                      ⏰ <span className="font-medium">{p.time}</span>
                    </p>
                  )}

                  {/* Day */}
                  {p.day && (
                    <p className="text-gray-700">
                      📅 <span className="font-medium">{p.day}</span>
                    </p>
                  )}

                  {/* Cost */}
                  {costLabel && (
                    <p className="text-gray-700">
                      💰 <span className="font-medium">{costLabel}</span>
                    </p>
                  )}

                  {/* Age */}
                  {ageLabel && (
                    <p className="text-gray-700 mt-1">
                      👶 연령: {ageLabel}
                    </p>
                  )}
                </div>
              );
            })
        )}

        {/* Kakao Map Link */}
        <a
          className="text-blue-600 underline mt-4 block text-center font-medium hover:text-blue-800"
          href={`https://map.kakao.com/link/map/${facility.name},${facility.lat},${facility.lon}`}
          target="_blank"
        >
          카카오맵에서 위치 보기
        </a>
      </div>
    </div>
  );
}
