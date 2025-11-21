export default function FacilityCard({ facility, onClose }: any) {
  if (!facility) return null;

  return (
    <div className="absolute bottom-4 left-4 bg-white shadow-xl rounded-lg p-4 w-96 z-50 max-h-96 overflow-auto">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold">{facility.name}</h2>
        <button className="text-gray-500" onClick={onClose}>✕</button>
      </div>

      <p className="text-gray-700">{facility.address}</p>

      <h3 className="mt-3 font-semibold">프로그램 목록</h3>

      {facility.programs.map((p: any, idx: number) => (
        <div key={idx} className="mt-2 p-2 border rounded">
          {p.note && <p className="text-sm">메모: {p.note}</p>}
          {p.time && <p className="text-sm">시간: {p.time}</p>}
          {p.day && <p className="text-sm">요일: {p.day}</p>}
          {p.cost && <p className="text-sm">비용: {p.cost}원</p>}
          {(p.age_min || p.age_max) && (
            <p className="text-sm">
              연령: {p.age_min} ~ {p.age_max}세
            </p>
          )}
        </div>
      ))}

      <a
        className="text-blue-600 underline block mt-3"
        href={`https://map.kakao.com/link/map/${facility.name},${facility.lat},${facility.lon}`}
        target="_blank"
      >
        카카오맵에서 보기
      </a>
    </div>
  );
}
