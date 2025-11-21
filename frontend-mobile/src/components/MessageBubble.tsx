import React from "react";
import { View, Text, TouchableOpacity, Linking, StyleSheet } from "react-native";
import Markdown from "react-native-markdown-display";
import type { MessageRole } from "../types";

interface Props {
  role: MessageRole;
  content: string;
  link?: string;
}

const MessageBubble: React.FC<Props> = ({ role, content, link }) => {
  const isUser = role === "user";

  const handleLinkPress = () => {
    if (link) {
      Linking.openURL(link);
    }
  };

  return (
    <View style={[styles.container, isUser ? styles.userContainer : styles.aiContainer]}>
      <View
        style={[
          styles.bubble,
          link
            ? styles.transparentBubble
            : isUser
            ? styles.userBubble
            : styles.aiBubble,
        ]}
      >
        <Markdown
          style={isUser ? markdownStylesUser : markdownStylesAi}
        >
          {content}
        </Markdown>

        {link && (
          <TouchableOpacity style={styles.linkButton} onPress={handleLinkPress}>
            <Text style={styles.linkButtonText}>📍 지도 보기</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
  },
  userContainer: {
    justifyContent: "flex-end",
  },
  aiContainer: {
    justifyContent: "flex-start",
  },
  bubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
  },
  userBubble: {
    backgroundColor: "#bbf7d0", // green-200
    borderBottomRightRadius: 0,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  aiBubble: {
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
  transparentBubble: {
    backgroundColor: "transparent",
  },
  linkButton: {
    marginTop: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: "#facc15", // yellow-400
    borderRadius: 8,
    alignSelf: "flex-start",
  },
  linkButtonText: {
    color: "#1f2937", // gray-800
    fontSize: 14,
    fontWeight: "500",
  },
});

const markdownStylesUser = StyleSheet.create({
  body: {
    fontSize: 14,
    lineHeight: 20,
    color: "#1f2937", // gray-800
  },
  paragraph: {
    marginVertical: 4,
  },
  link: {
    color: "#2563eb",
    textDecorationLine: "underline",
  },
});

const markdownStylesAi = StyleSheet.create({
  body: {
    fontSize: 14,
    lineHeight: 20,
    color: "#374151", // gray-700
  },
  paragraph: {
    marginVertical: 4,
  },
  link: {
    color: "#2563eb",
    textDecorationLine: "underline",
  },
});

export default MessageBubble;
