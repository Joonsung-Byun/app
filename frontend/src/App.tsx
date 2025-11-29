import React from "react";
import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import HeroPage from "./pages/HeroPage";
import ChatPage from "./pages/ChatPage";
import Map from "./pages/Map";

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 via-white to-green-50 text-slate-900">
      <Routes>
        <Route path="/" element={<HeroPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/map" element={<Map />} />
      </Routes>
    </div>
  );
};

export default App;
