import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import TextLesson from "../lessons/01-text";
import StyleLesson from "../lessons/02-style";
import ImageLesson from "../lessons/03-image";

export default function BasicsScreen() {
  const [step, setStep] = useState(1);

  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>从一行文字开始</Text>
        <Text style={styles.hint}>
          按顺序点三个按钮，看同一块内容逐步变化。
        </Text>
        <View style={styles.steps}>
          {["1 文字", "2 样式", "3 图片"].map((label, index) => (
            <Pressable
              key={label}
              accessibilityRole="button"
              accessibilityState={{ selected: step === index + 1 }}
              style={[styles.button, step === index + 1 && styles.selected]}
              onPress={() => setStep(index + 1)}
            >
              <Text
                style={
                  step === index + 1 ? styles.activeText : styles.buttonText
                }
              >
                {label}
              </Text>
            </Pressable>
          ))}
        </View>
        <Text style={styles.hint}>
          下面显示的是第 {step} 个练习文件的内容：
        </Text>
        {step === 1 ? <TextLesson /> : null}
        {step === 2 ? <StyleLesson /> : null}
        {step === 3 ? <ImageLesson /> : null}
        <Text style={styles.hint}>
          打开 lessons/
          {step === 1 ? "01-text" : step === 2 ? "02-style" : "03-image"}
          .tsx，改文字或样式，保存后看这里。
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  content: { padding: 20, gap: 20 },
  title: { fontSize: 26, fontWeight: "700", color: "#234536" },
  hint: { fontSize: 15, lineHeight: 24, color: "#615D50" },
  steps: { flexDirection: "row", gap: 8 },
  button: {
    flex: 1,
    paddingVertical: 14,
    alignItems: "center",
    borderRadius: 10,
    backgroundColor: "#FFFCF5",
  },
  selected: { backgroundColor: "#234536" },
  buttonText: { color: "#234536", fontSize: 16 },
  activeText: { color: "#FFFCF5", fontSize: 16 },
});
