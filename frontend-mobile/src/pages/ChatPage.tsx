import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import ExamplePrompts from "../components/ExamplePrompts";
import { useChatStorage } from "../hooks/useChatStorage";
import type { Message } from "../types";

const ChatPage: React.FC = () => {
  const { messages, addMessage, clearMessages, isLoaded } = useChatStorage();
  const [message, setMessage] = useState("");
  const [started, setStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 로딩 완료 후 메시지가 있으면 started를 true로
  useEffect(() => {
    if (isLoaded && messages.length > 0) {
      setStarted(true);
    }
  }, [isLoaded, messages.length]);

  useEffect(() => {
    // conversation_id가 없으면 새로 생성
    const initConversationId = async () => {
      const conversationId = await AsyncStorage.getItem("conversation_id");
      if (!conversationId) {
        const uuid = generateUUID();
        await AsyncStorage.setItem("conversation_id", uuid);
      }
    };
    initConversationId();
  }, []);


  const generateUUID = () => {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  };

  const handlePromptClick = (prompt: string) => {
    setMessage(prompt);
  };

  const handleSend = async (userMessage: string) => {
    if (!started) setStarted(true);

    const userMsg: Message = {
      role: "user",
      content: userMessage,
      type: "text",
    };
    addMessage(userMsg);
    setIsLoading(true);

    try {
      const conversationId =
        (await AsyncStorage.getItem("conversation_id")) || "";

      const response = await fetch("http://localhost:8080/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.conversation_id) {
        await AsyncStorage.setItem("conversation_id", data.conversation_id);
      }

      if (data.type === "map") {
        let mapData = data.data;

        if (!Array.isArray(mapData)) {
          if (mapData.address && !mapData.desc) {
            mapData.desc = mapData.address;
          }
          mapData = [mapData];
        }

        const mapMsg: Message = {
          role: "ai",
          type: "map",
          content: data.content || "위치를 지도에 표시해 드려요! 📍",
          link: data.link,
          data: mapData,
        };
        addMessage(mapMsg);
      } else {
        const textMsg: Message = {
          role: "ai",
          type: "text",
          content: data.content,
        };
        addMessage(textMsg);
      }
    } catch (error) {
      console.error("API 호출 오류:", error);

      const errorMsg: Message = {
        role: "ai",
        type: "text",
        content: "죄송해요, 일시적인 오류가 발생했어요. 다시 시도해주세요. 😢",
      };
      addMessage(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
    >
      <View style={styles.inner}>
        {started && (
          <View style={styles.header}>
            <Image
              source={require("../../assets/logo2_copy.webp")}
              style={styles.headerLogo}
              resizeMode="contain"
            />
          </View>
        )}

        {/* Hero Screen */}
        {!started && (
          <View style={styles.heroContainer}>
            <View style={styles.heroContent}>
              <View style={styles.logoContainer}>
                <Image
                  source={require("../../assets/logo_copy.webp")}
                  style={styles.heroLogo}
                  resizeMode="contain"
                />
              </View>
              <Text style={styles.heroTitle}>아이와 주말 나들이 어때요?</Text>
              <Text style={styles.heroSubtitle}>
                지역·날씨·아이 연령에 맞는 장소를 챗봇이 추천해드릴게요.
              </Text>
            </View>

            <InputBox
              variant="hero"
              message={message}
              setMessage={setMessage}
              onSend={handleSend}
            />

            <View style={styles.promptsContainer}>
              <ExamplePrompts onPromptClick={handlePromptClick} />
            </View>
          </View>
        )}

        {/* Chat Screen */}
        {started && (
          <View style={styles.chatContainer}>
            <View style={styles.chatWindowWrapper}>
              <ChatWindow
                messages={messages}
                onPromptClick={handlePromptClick}
                isLoading={isLoading}
              />
            </View>

            <InputBox
              variant="chat"
              message={message}
              setMessage={setMessage}
              onSend={handleSend}
              isSending={isLoading}
            />

            <TouchableOpacity onPress={() => {
              clearMessages();
              setStarted(false);
            }} style={styles.clearButton}>
              <Text style={styles.clearButtonText}>대화 초기화</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
};

const { width, height } = Dimensions.get("window");

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f0fdf4", // green-50
  },
  inner: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 40,
  },
  header: {
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    marginBottom: 12,
  },
  headerLogo: {
    width: 144, // w-36
    height: 60,
  },
  headerTitle: {
    fontSize: 20, // text-xl
    fontWeight: "700",
  },
  heroContainer: {
    flex: 1,
    justifyContent: "center",
  },
  heroContent: {
    alignItems: "center",
    marginBottom: 32,
  },
  logoContainer: {
    alignItems: "center",
    marginBottom: 12,
  },
  heroLogo: {
    width: width * 0.4, // w-36 to w-72 responsive
    height: 150,
  },
  heroTitle: {
    fontSize: 32, // text-4xl
    fontWeight: "600",
    color: "#3a3a35",
    marginBottom: 12,
    textAlign: "center",
    letterSpacing: -0.5,
  },
  heroSubtitle: {
    fontSize: 14, // text-sm
    color: "#9a9081",
    textAlign: "center",
  },
  promptsContainer: {
    marginTop: 24,
    alignItems: "center",
  },
  chatContainer: {
    flex: 1,
  },
  chatWindowWrapper: {
    flex: 1,
    marginBottom: 16,
  },
  clearButton: {
    marginTop: 8,
    alignSelf: "center",
  },
  clearButtonText: {
    fontSize: 12, // text-xs
    color: "#9ca3af", // gray-400
    textDecorationLine: "underline",
  },
});

export default ChatPage;
