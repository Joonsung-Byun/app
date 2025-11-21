import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";

interface Props {
  onPromptClick: (text: string) => void;
}

const prompts = [
  "🌳 주말에 아이랑 갈만한 부산 공원 추천",
  "🎨 비 오는 날 서울 실내 체험장 알려줘",
  "🚴 성수동 근처 자전거 탈 수 있는 곳",
];

const ExamplePrompts: React.FC<Props> = ({ onPromptClick }) => {
  return (
    <View style={styles.container}>
      {prompts.map((text, i) => (
        <TouchableOpacity
          key={i}
          onPress={() => onPromptClick(text)}
          style={styles.prompt}
          activeOpacity={0.7}
        >
          <Text style={styles.promptText}>{text}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 12,
  },
  prompt: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#bbf7d0", // green-200
    borderRadius: 9999,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  promptText: {
    fontSize: 14,
    color: "#374151", // gray-700
  },
});

export default ExamplePrompts;
