import React from "react";
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
} from "react-native";

interface Props {
  message: string;
  setMessage: (value: string) => void;
  onSend: (message: string) => void;
  variant?: "hero" | "chat";
}

const InputBox: React.FC<Props> = ({
  message,
  setMessage,
  onSend,
  variant = "chat",
}) => {
  const handleSubmit = () => {
    if (!message.trim()) return;
    onSend(message);
    setMessage("");
  };

  return (
    <View
      style={[
        styles.container,
        variant === "hero" ? styles.heroContainer : styles.chatContainer,
      ]}
    >
      <TextInput
        placeholder="어디로 나들이 가고 싶으신가요?"
        placeholderTextColor="#9ca3af"
        value={message}
        onChangeText={setMessage}
        onSubmitEditing={handleSubmit}
        style={styles.input}
        returnKeyType="send"
      />
      <TouchableOpacity
        onPress={handleSubmit}
        style={styles.button}
        activeOpacity={0.8}
      >
        <Text style={styles.buttonText}>보내기</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  heroContainer: {
    borderWidth: 1,
    borderColor: "#e0d6c7",
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  chatContainer: {
    borderWidth: 1,
    borderColor: "#e5e7eb", // gray-200
  },
  input: {
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    color: "#374151", // gray-700
  },
  button: {
    backgroundColor: "#e79f85",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "500",
    fontSize: 16,
  },
});

export default InputBox;
