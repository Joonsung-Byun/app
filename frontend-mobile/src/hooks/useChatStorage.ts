import { useState, useEffect } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { Message } from "../types";

export function useChatStorage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    // Load messages from AsyncStorage on mount
    const loadMessages = async () => {
      try {
        const saved = await AsyncStorage.getItem("chatMessages");
        if (saved) {
          setMessages(JSON.parse(saved));
        }
      } catch (error) {
        console.error("Failed to load messages:", error);
      } finally {
        setIsLoaded(true);
      }
    };
    loadMessages();
  }, []);

  useEffect(() => {
    // Save messages to AsyncStorage whenever they change
    const saveMessages = async () => {
      try {
        await AsyncStorage.setItem("chatMessages", JSON.stringify(messages));
      } catch (error) {
        console.error("Failed to save messages:", error);
      }
    };
    if (messages.length > 0) {
      saveMessages();
    }
  }, [messages]);

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const clearMessages = async () => {
    try {
      await AsyncStorage.removeItem("chatMessages");
      setMessages([]);
    } catch (error) {
      console.error("Failed to clear messages:", error);
    }
  };

  return { messages, addMessage, clearMessages, isLoaded };
}
