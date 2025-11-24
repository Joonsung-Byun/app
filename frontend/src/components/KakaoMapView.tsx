import React, { useEffect, useRef, useState } from "react";
import type { MapData } from "../types";

interface Props {
  data: MapData;
  link?: string;
}

// Kakao 타입 선언
declare global {
  interface Window {
    kakao: any;
  }
}

const KakaoMapView: React.FC<Props> = ({ data, link }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const parkingMarkersRef = useRef<any[]>([]);
  const placesRef = useRef<any | null>(null);
  const parkingInfoRef = useRef<{ marker: any; infowindow: any } | null>(null);
  const [isParkingVisible, setIsParkingVisible] = useState(false);

  useEffect(() => {
    // 이미 스크립트가 로드되어 있는지 확인
    if (window.kakao && window.kakao.maps) {
      initMap();
      return;
    }

    // 스크립트 로드
    const script = document.createElement("script");
    script.src = import.meta.env.VITE_KAKAO_MAP_URL;
    console.log(import.meta.env.VITE_KAKAO_MAP_URL);
    script.async = true;
    
    script.onload = () => {
      // kakao.maps.load()를 통해 실제로 라이브러리를 로드
      window.kakao.maps.load(() => {
        console.log("Kakao Maps loaded successfully");
        initMap();
      });
    };

    script.onerror = (e) => {
      console.log(e)
      console.error("Failed to load Kakao Maps script");
    };

    document.head.appendChild(script);

    return () => {
      // cleanup: 스크립트 제거는 하지 않음 (재사용을 위해)
    };
  }, [data]);

  const clearParkingMarkers = () => {
    parkingMarkersRef.current.forEach((m) => m.setMap(null));
    parkingMarkersRef.current = [];

    if (parkingInfoRef.current) {
      parkingInfoRef.current.infowindow.close();
      parkingInfoRef.current = null;
    }
  };

  const initMap = () => {
    if (!mapContainerRef.current) return;

    try {
      const { kakao } = window;
      
      const options = {
        center: new kakao.maps.LatLng(data.center.lat, data.center.lng),
        level: 4,
      };
      
      const map = new kakao.maps.Map(mapContainerRef.current, options);
      mapRef.current = map;

      // 마커 추가
      data.markers.forEach((m) => {
        const marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(m.lat, m.lng),
          map,
        });

        const infowindow = new kakao.maps.InfoWindow({
          content: `<div style="padding:8px 12px;font-size:14px;">${m.name}<br/><span style="color:#666;font-size:12px;">${m.desc ?? ""}</span></div>`,
        });

        kakao.maps.event.addListener(marker, "click", () => {
          infowindow.open(map, marker);
        });
      });

      // 지도 빈 공간 클릭 시 주차장 인포윈도우 닫기
      kakao.maps.event.addListener(map, "click", () => {
        if (parkingInfoRef.current) {
          parkingInfoRef.current.infowindow.close();
          parkingInfoRef.current = null;
        }
      });

      console.log("Map initialized successfully");
    } catch (error) {
      console.error("Error initializing map:", error);
    }
  };

  const handleSearchParking = () => {
    if (!window.kakao || !window.kakao.maps || !mapRef.current) return;

    // 토글: 이미 표시 중이면 모두 숨기기
    if (isParkingVisible) {
      clearParkingMarkers();
      setIsParkingVisible(false);
      return;
    }

    console.log("Searching for parking lots...");
    const { kakao } = window;
    console.log("Kakao maps object:", kakao.maps);
    const map = mapRef.current;
    console.log("Map object:", map);

    if (!kakao.maps.services) return;
    console.log("Kakao maps services object:", kakao.maps.services);

    if (!placesRef.current) {
      placesRef.current = new kakao.maps.services.Places(map);
    }

    const ps = placesRef.current;
    console.log("Places service initialized:", ps);

    const callback = (data: any[], status: any) => {
      const { Status } = kakao.maps.services;

      if (status !== Status.OK) {
        clearParkingMarkers();
        return;
      }

      clearParkingMarkers();

      data.forEach((place) => {
        const position = new kakao.maps.LatLng(place.y, place.x);

        // 주차장용 커스텀 마커 이미지 (public/parking1.svg 사용)
        const imageSrc = "/parking1.svg";
        const imageSize = new kakao.maps.Size(24, 28);
        const markerImage = new kakao.maps.MarkerImage(imageSrc, imageSize);

        const marker = new kakao.maps.Marker({
          position,
          image: markerImage,
          map,
        });

        const content = `
          <div style="padding:8px 12px;font-size:13px;">
            <strong>${place.place_name}</strong><br/>
            <span style="color:#666;">${place.road_address_name || place.address_name || ""}</span><br/>
            ${place.phone ? `<span style="color:#999;font-size:11px;">${place.phone}</span>` : ""}
          </div>
        `;

        const infowindow = new kakao.maps.InfoWindow({ content });

        kakao.maps.event.addListener(marker, "click", () => {
          // 같은 마커를 다시 클릭하면 토글로 닫기
          if (parkingInfoRef.current?.marker === marker) {
            parkingInfoRef.current?.infowindow.close();
            parkingInfoRef.current = null;
            return;
          }

          // 다른 주차장 인포윈도우가 열려 있으면 먼저 닫기
          if (parkingInfoRef.current) {
            parkingInfoRef.current.infowindow.close();
          }

          infowindow.open(map, marker);
          parkingInfoRef.current = { marker, infowindow };
        });

        parkingMarkersRef.current.push(marker);
      });

      setIsParkingVisible(true);
    };

    ps.categorySearch("PK6", callback, { useMapBounds: true });
  };

  return (
    <div className="w-full md:w-1/2 mb-3">
      <div className="flex items-center justify-between mb-2 gap-2">
        {link && (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-4 py-2 bg-yellow-400 text-gray-800 rounded-lg hover:bg-yellow-500 transition-colors text-xs md:text-sm font-medium"
          >
            📍 지도 보기
          </a>
        )}
        <div className="flex-1 flex justify-end">
          <button
            type="button"
            onClick={handleSearchParking}
            className={`px-3 py-1.5 rounded-full border text-xs md:text-sm shadow-sm transition-colors hover:cursor-pointer ${
              isParkingVisible
                ? "bg-green-600 text-white border-green-600 hover:bg-green-700"
                : "bg-white/80 text-green-700 border-green-300 hover:bg-green-50"
            }`}
          >
            {isParkingVisible ? "🚗 주차장 숨기기" : "🚗 주변 주차장 보기"}
          </button>
        </div>
      </div>
      <div
        ref={mapContainerRef}
        className="w-full h-64 rounded-xl border border-green-300 shadow-sm"
      />
    </div>
  );
};

export default KakaoMapView;
