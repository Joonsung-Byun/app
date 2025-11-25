import { useEffect, useRef, useState } from "react";
import FacilityModal from "../components/FacilityModal";
import { fetchFacilities } from "../libs/fetchFacilities";
import { fetchPrograms } from "../libs/fetchPrograms";

declare global {
  interface Window {
    kakao: any;
  }
}

export default function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObjRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  const [selected, setSelected] = useState<any>(null);
  const [kakaoLoaded, setKakaoLoaded] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProgramsLoading, setIsProgramsLoading] = useState(false);

  const CATEGORIES = [
  { emoji: "🏃", label: "생활체육관", value: "생활체육관" },
  { emoji: "🖼️", label: "전시", value: "전시/기념관" },
  { emoji: "📍", label: "관광지", value: "관광지" },
  { emoji: "🧸", label: "실내놀이시설", value: "실내놀이시설" },
  { emoji: "🌳", label: "실외놀이시설", value: "실외놀이시설" },
  //영화
  { emoji: "🎬", label: "영화/연극", value: "영화/연극/공연" },
];

  // ---------- Kakao JS SDK load ----------
  useEffect(() => {
    const script = document.createElement("script");
    script.src = import.meta.env.VITE_KAKAO_MAP_URL;

    script.onload = () => {
      window.kakao.maps.load(() => setKakaoLoaded(true));
    };

    document.head.appendChild(script);
  }, []);

  useEffect(() => {
    console.log(selected);
  }, [selected]);

  // ---------- Map initialization ----------
  useEffect(() => {
    if (!kakaoLoaded || !mapRef.current) return;

    const savedLat = localStorage.getItem("map_center_lat");
    const savedLon = localStorage.getItem("map_center_lon");

    const center =
      savedLat && savedLon
        ? new window.kakao.maps.LatLng(
            parseFloat(savedLat),
            parseFloat(savedLon)
          )
        : new window.kakao.maps.LatLng(37.4979, 127.0276);

    const map = new window.kakao.maps.Map(mapRef.current, {
      center,
      level: 7,
    });

    mapObjRef.current = map;
  }, [kakaoLoaded]);

  // ---------- Save map center ----------
  useEffect(() => {
    if (!kakaoLoaded) return;

    const map = mapObjRef.current;
    if (!map) return;

    window.kakao.maps.event.addListener(map, "idle", () => {
      const center = map.getCenter();
      localStorage.setItem("map_center_lat", center.getLat());
      localStorage.setItem("map_center_lon", center.getLng());
    });
  }, [kakaoLoaded]);

  // ---------- Calculate map bounds ----------
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

  // ---------- Render markers ----------
const renderMarkers = (items: any[]) => {
  const map = mapObjRef.current;

  markersRef.current.forEach((m) => m.setMap(null));
  markersRef.current = [];

  items.forEach((f: any) => {
    const marker = new window.kakao.maps.Marker({
      position: new window.kakao.maps.LatLng(f.lat, f.lon),
      map,
    });

    markersRef.current.push(marker);

    window.kakao.maps.event.addListener(marker, "click", async () => {
      const baseData = { ...f, programs: [] };
      setSelected(baseData);
      setIsProgramsLoading(true);

      try {
        const programs = await fetchPrograms(f.id);
        setSelected({
          ...f,
          programs: programs || [],
        });
      } catch (error) {
        console.error("Failed to fetch programs", error);
        setSelected({
          ...f,
          programs: [],
        });
      } finally {
        setIsProgramsLoading(false);
      }
    });
  });
};

  // ---------- Category click ----------
  async function handleCategorySelect(category: string) {
    const bounds = getMapBounds();
    const items = await fetchFacilities(category, bounds);
    renderMarkers(items);
  }

  return (
    <div className="relative w-full min-h-screen flex flex-col items-center gap-4 px-4 pt-20 pb-4 md:pt-20">
      {/* Header */}
      {/* <div className="flex justify-center items-center gap-5">
        <img
          src="/logo2_copy.webp"
          alt=""
          className="w-36 md:w-52 h-auto block"
        />
      </div> */}

      <div className="relative w-full max-w-6xl h-[80vh] md:w-4/5 rounded-xl shadow-xl overflow-hidden mx-4 lg:mx-0 border border-green-300">
        {/* Category buttons */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 w-full px-3 lg:top-4 lg:px-0">
          {/* Mobile: ... button + dropdown */}
          <div className="lg:hidden flex justify-end">
            <div className="relative inline-block text-left">
              <button
                className="flex items-center justify-center px-3 py-1.5 bg-white rounded-full border border-gray-300 shadow-md text-sm font-medium hover:bg-gray-50 transition hover:cursor-pointer"
                onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              >
                <span className="text-2xl">•••</span>
              </button>
              {isMobileMenuOpen && (
                <div className="absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.value}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-left  hover:bg-gray-100 transition hover:cursor-pointer"
                      onClick={() => {
                        handleCategorySelect(cat.value);
                        setIsMobileMenuOpen(false);
                      }}
                    >
                      <span>{cat.emoji}</span>
                      <span>{cat.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Desktop: pill menu */}
          <div className="hidden lg:flex items-center gap-2  px-2 py-2 rounded-full  overflow-x-auto max-w-full">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                className="flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-300 shadow-md text-sm font-medium hover:bg-gray-50 transition hover:cursor-pointer whitespace-nowrap"
                onClick={() => handleCategorySelect(cat.value)}
              >
                <span>{cat.emoji}</span>
                <span className="font-semibold">{cat.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* MAP */}
        <div ref={mapRef} className="w-full h-full" />

        {selected && (
          <FacilityModal
            facility={selected}
            onClose={() => setSelected(null)}
            isProgramsLoading={isProgramsLoading}
          />
        )}
      </div>
    </div>
  );
}
