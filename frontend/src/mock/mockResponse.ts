import type { Message } from "../types";

export function mockChatAPI(userMessage: string): Promise<Message> {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (userMessage.includes("한남동")) {
        resolve(
          {
          role: "ai",
          type: "map",
          content: "",
          link: "https://map.kakao.com/link/to/강남어린이공원,37.4979,127.0276",
          data: {
            center: { lat: 37.533, lng: 127.002 },
            markers: [
              { name: "한남어린이공원", lat: 37.5341, lng: 127.0013, desc: "그늘 많음" },
            ]
          }
        }
      );
      } 
      else if (userMessage.includes("성수동")) {
        resolve({
          role: "ai",
          type: "map",
          content: "",
          link: "https://map.kakao.com/link/to/뚝섬한강공원,37.5445,127.0560",
          data: {
            center: { lat: 37.544, lng: 127.056 },
            markers: [
              { name: "뚝섬한강공원", lat: 37.5445, lng: 127.0560, desc: "자전거 대여소 있음" },
              { name: "서울숲", lat: 37.5449, lng: 127.0406, desc: "자전거 도로 완비" }
            ]
          }
        });
      }
      else {
        resolve({
          role: "ai",
          type: "text",
          content: `“${userMessage}” 에 대한 정보를 준비 중이에요 💬`,
        });
      }
    }, 500);
  });
}
