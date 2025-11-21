import React, { useEffect, useRef, useState } from "react";
import FacilityCard from "../components/FacilityCard";
import { groupByFacility } from "../libs/groupFacilities";

declare global {
  interface Window {
    kakao: any;
  }
}

async function fetchFacilities(category2?: string, bounds?: any) {
  if (!bounds) return [];

  const { minLat, maxLat, minLon, maxLon } = bounds;

  let url = `http://localhost:8080/facilities?minLat=${minLat}&maxLat=${maxLat}&minLon=${minLon}&maxLon=${maxLon}`;
  console.log("Fetching from URL:", url);

  if (category2) {
    url += `&category2=${category2}`;
  }

  const res = await fetch(url);
  return await res.json();
}

export default function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObjRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  const [selected, setSelected] = useState<any>(null);
  const [kakaoLoaded, setKakaoLoaded] = useState(false);

  // ---------- 카카오 JS SDK 로딩 ----------
  useEffect(() => {
    const script = document.createElement("script");
    script.src = import.meta.env.VITE_KAKAO_MAP_URL;

    script.onload = () => {
      window.kakao.maps.load(() => {
        setKakaoLoaded(true);
      });
    };

    document.head.appendChild(script);
  }, []);

  // ---------- 지도 초기화 ----------
  useEffect(() => {
    if (!kakaoLoaded || !mapRef.current) return;

    const center = new window.kakao.maps.LatLng(37.4979, 127.0276);
    const map = new window.kakao.maps.Map(mapRef.current, {
      center,
      level: 5,
    });

    mapObjRef.current = map;
  }, [kakaoLoaded]);

  // ---------- 지도 Bounds 구하는 함수 ----------
  const getMapBounds = () => {
    const map = mapObjRef.current;
    if (!map) return null;

    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    return {
      minLat: sw.getLat(),
      minLon: sw.getLng(),
      maxLat: ne.getLat(),
      maxLon: ne.getLng(),
    };
  };

  // ---------- 지도 이동될 때마다 시설 자동 로드 ----------
useEffect(() => {
  if (!kakaoLoaded) return;

  const map = mapObjRef.current;
  if (!map) return;

  window.kakao.maps.event.addListener(map, "idle", () => {
    // 위치 저장만 수행
    const center = map.getCenter();
    localStorage.setItem("map_center_lat", center.getLat());
    localStorage.setItem("map_center_lon", center.getLng());
  });
}, [kakaoLoaded]);
  // ---------- 마커 렌더링 ----------
  const renderMarkers = (items: any[]) => {
    console.log(items, "Rendering markers for items:");
    const map = mapObjRef.current;

    // 이전 마커 제거
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    const grouped = groupByFacility(items);

    grouped.forEach((f: any) => {
      const marker = new window.kakao.maps.Marker({
        position: new window.kakao.maps.LatLng(f.lat, f.lon),
        map,
      });

      markersRef.current.push(marker);

      window.kakao.maps.event.addListener(marker, "click", () => {
        setSelected(f);
      });
    });
    console.log("Markers rendered:", markersRef.current.length);
  };

  // ---------- 카테고리 선택 시 ----------
  async function handleCategorySelect(category: string) {
    const bounds = getMapBounds();
    const items = await fetchFacilities(category, bounds);
    renderMarkers(items);
  }

  return (
    <div className="relative w-full h-screen flex items-center justify-center">
      <div className="relative w-4/5 h-4/5 border rounded-xl shadow-xl overflow-hidden">

        {/* 카테고리 버튼 */}
        <div className="absolute top-4 left-4 bg-white p-3 shadow-lg rounded-lg z-50 flex gap-2">
          <button
            className="px-3 py-1 bg-blue-500 text-white rounded"
            onClick={() => handleCategorySelect("생활체육관")}
          >
            생활체육관
          </button>

          <button
            className="px-3 py-1 bg-green-500 text-white rounded"
            onClick={() => handleCategorySelect("놀이")}
          >
            놀이
          </button>

          <button
            className="px-3 py-1 bg-purple-500 text-white rounded"
            onClick={() => handleCategorySelect("전시/기념관")}
          >
            전시
          </button>
        </div>

        <div ref={mapRef} className="w-full h-full" />
      </div>

      {selected && (
        <FacilityCard
          facility={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
