import React from "react";

export default function FacilityModal({ facility, onClose }: any) {
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

  const placeTypeColor =
    in_out === "실내"
      ? "bg-blue-100 text-blue-600"
      : in_out === "실외"
      ? "bg-green-100 text-green-600"
      : "bg-gray-100 text-gray-600";

  const catColor = "bg-purple-100 text-purple-600";

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto p-6 animate-fadeIn">

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

        {/* Program List */}
        <h3 className="font-semibold text-lg mb-3">프로그램 목록</h3>

        {programs.length === 0 ? (
          <div className="p-4 text-center text-gray-500 border rounded-lg">
            등록된 프로그램 정보가 없어요.
          </div>
        ) : (
          programs.map((p: any, idx: number) => (
            <div
              key={idx}
              className="mb-3 p-3 border rounded-xl bg-gray-50 shadow-sm"
            >
              {/* Note (시설 설명/부가정보) */}
              {p.note && (
                <p className="text-sm mb-2 text-gray-900 font-medium">
                  {p.note}
                </p>
              )}

              {/* Time */}
              {p.time && (
                <p className="text-sm text-gray-700">
                  ⏰ <span className="font-medium">{p.time}</span>
                </p>
              )}

              {/* Day */}
              {p.day && (
                <p className="text-sm text-gray-700">
                  📅 <span className="font-medium">{p.day}</span>
                </p>
              )}

              {/* Cost */}
              {p.cost && (
                <p className="text-sm text-gray-700">
                  💰 {p.cost.toLocaleString()}원
                </p>
              )}

              {/* Age */}
              {(p.age_min || p.age_max) && (
                <p className="text-sm text-gray-700">
                  👶 연령: {p.age_min ?? "?"} ~ {p.age_max ?? "?"}세
                </p>
              )}
            </div>
          ))
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
