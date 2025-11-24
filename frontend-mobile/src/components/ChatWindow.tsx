import React, { useRef, useEffect } from "react";
import { View, ScrollView, StyleSheet } from "react-native";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import KakaoMapView from "./KakaoMapView";
import ExamplePrompts from "./ExamplePrompts";
import TypingIndicator from "./TypingIndicator";

interface Props {
  messages: Message[];
  onPromptClick: (prompt: string) => void;
  isLoading: boolean;
}

const ChatWindow: React.FC<Props> = ({ messages, onPromptClick, isLoading }) => {
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages, isLoading]);

  return (
    <ScrollView
      ref={scrollRef}
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      showsVerticalScrollIndicator={false}
    >
      {messages.length === 0 ? (
        <View style={styles.emptyContainer}>
          <ExamplePrompts onPromptClick={onPromptClick} />
        </View>
      ) : (
        <>
          {messages.map((msg, i) => (
            <View key={i} style={styles.messageWrapper}>
              {msg.type === "map" ? (
                <>
                  <MessageBubble
                    role={msg.role}
                    content={msg.content}
                    link={msg.link}
                  />
                  {msg.data && <KakaoMapView data={msg.data} />}
                </>
              ) : (
                <MessageBubble role={msg.role} content={msg.content} />
              )}
            </View>
          ))}

          {isLoading && (
            <View style={styles.loadingContainer}>
              <View style={styles.loadingBubble}>
                <TypingIndicator />
              </View>
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    maxHeight: "100%",
    backgroundColor: "rgba(255, 255, 255, 0.7)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#dcfce7", // green-100
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  contentContainer: {
    padding: 24,
    gap: 12,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 16,
  },
  messageWrapper: {
    marginBottom: 12,
  },
  loadingContainer: {
    flexDirection: "row",
    justifyContent: "flex-start",
  },
  loadingBubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
    backgroundColor: "#f3f4f6", // gray-100
    borderWidth: 1,
    borderColor: "#e5e7eb", // gray-200
    borderBottomLeftRadius: 0,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
});

export default ChatWindow;
