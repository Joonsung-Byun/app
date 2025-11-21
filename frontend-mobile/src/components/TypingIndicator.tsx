import React, { useState, useEffect, useRef } from "react";
import { View, Text, Animated, StyleSheet } from "react-native";

const MESSAGES = [
  "장소 정보를 찾는 중..",
  "해당 장소 특이사항 분석 중..",
  "응답을 생성하는 중..",
];

const TypingIndicator: React.FC = () => {
  const [messageIndex, setMessageIndex] = useState(0);

  // Animated values for bounce effect
  const bounce1 = useRef(new Animated.Value(0)).current;
  const bounce2 = useRef(new Animated.Value(0)).current;
  const bounce3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Bounce animation
    const createBounce = (value: Animated.Value, delay: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(value, {
            toValue: -6,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(value, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ])
      );
    };

    const anim1 = createBounce(bounce1, 0);
    const anim2 = createBounce(bounce2, 200);
    const anim3 = createBounce(bounce3, 400);

    anim1.start();
    anim2.start();
    anim3.start();

    return () => {
      anim1.stop();
      anim2.stop();
      anim3.stop();
    };
  }, []);

  useEffect(() => {
    if (messageIndex >= MESSAGES.length - 1) {
      return;
    }

    const interval = setInterval(() => {
      setMessageIndex((prev) => {
        if (prev >= MESSAGES.length - 1) {
          return prev;
        }
        return prev + 1;
      });
    }, 4000);

    return () => clearInterval(interval);
  }, [messageIndex]);

  useEffect(() => {
    setMessageIndex(0);
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.dotsContainer}>
        <Animated.View
          style={[styles.dot, { transform: [{ translateY: bounce1 }] }]}
        />
        <Animated.View
          style={[styles.dot, { transform: [{ translateY: bounce2 }] }]}
        />
        <Animated.View
          style={[styles.dot, { transform: [{ translateY: bounce3 }] }]}
        />
      </View>
      <Text style={styles.message}>{MESSAGES[messageIndex]}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  dotsContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#6b7280", // gray-500
  },
  message: {
    fontSize: 14,
    color: "#4b5563", // gray-600
  },
});

export default TypingIndicator;
