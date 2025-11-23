import { useEffect, useState } from "react";
import { fetchPrograms } from "../libs/fetchPrograms";

export default function FacilityPanel({ facility, onClose }: any) {
  const [programs, setPrograms] = useState<any[]>([]);

  useEffect(() => {
    async function load() {
      const data = await fetchPrograms(facility.id);
      setPrograms(data);
    }
    load();
  }, [facility]);

  return (
    <div className="absolute top-0 left-0 h-full w-96 bg-white shadow-xl z-50 p-5 overflow-y-auto">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">{facility.name}</h2>
        <button onClick={onClose} className="text-gray-500 text-2xl">✕</button>
      </div>

      <p className="text-gray-700 mb-4">{facility.address}</p>

      <h3 className="text-lg font-semibold mb-2">프로그램 목록</h3>

      {programs.length === 0 && (
        <p className="text-gray-500 text-sm">프로그램 정보를 불러오는 중...</p>
      )}

      {programs.map((p, i) => (
        <div key={i} className="border rounded p-3 mb-3 text-sm">
          {p.note && <p>메모: {p.note}</p>}
          {p.time && <p>시간: {p.time}</p>}
          {p.day && <p>요일: {p.day}</p>}
          {p.cost && <p>비용: {p.cost}원</p>}
          {(p.age_min || p.age_max) && <p>연령: {p.age_min} ~ {p.age_max}세</p>}
        </div>
      ))}

      <a
        className="text-blue-600 underline mt-3 block"
        href={`https://map.kakao.com/link/map/${facility.name},${facility.lat},${facility.lon}`}
        target="_blank"
      >
        카카오맵에서 보기
      </a>
    </div>
  );
}
