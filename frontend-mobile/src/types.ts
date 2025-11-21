export type MessageRole = "user" | "ai";

export interface MapMarker {
  name: string;
  lat: number;
  lng: number;
  desc?: string;
}

export interface MapData {
  center: { lat: number; lng: number };
  markers: MapMarker[];
}

export interface Message {
  role: "user" | "ai";
  content: string;
  type: "text" | "map";
  link?: string;
  data?: {
    center: { lat: number; lng: number };
    markers: Array<{
      name: string;
      lat: number;
      lng: number;
      desc?: string;
    }>;
  };
}
