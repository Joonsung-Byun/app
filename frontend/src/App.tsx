import React from "react";
import ChatPage from "./pages/ChatPage";

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-linear-to-b from-green-50 via-white to-green-50 flex items-center justify-center">
      <ChatPage />
    </div>
  );
};

export default App;
