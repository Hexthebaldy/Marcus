import { useState } from "react";
import { router } from "expo-router";
import { useHeaderHeight } from "expo-router/react-navigation";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNotes } from "../src/notes";

export default function ComposeScreen() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const { addNote } = useNotes();
  const headerHeight = useHeaderHeight();

  function publishNote() {
    if (!title.trim() || !body.trim()) {
      setError("请填写标题和正文，再发布。");
      return;
    }
    // 先更新页面共用的列表，再关闭编辑页回到首页。
    addNote(title.trim(), body.trim());
    router.dismissTo("/");
  }

  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.page}>
      <KeyboardAvoidingView
        style={styles.page}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={headerHeight}
      >
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.form}
        >
          <Text style={styles.label}>标题</Text>
          <TextInput
            accessibilityLabel="标题"
            placeholder="今天发现了什么？"
            value={title}
            onChangeText={setTitle}
            style={styles.input}
          />
          <Text style={styles.label}>正文</Text>
          <TextInput
            accessibilityLabel="正文"
            placeholder="写下你的体验……"
            value={body}
            onChangeText={setBody}
            multiline
            style={[styles.input, styles.bodyInput]}
          />
          {error ? (
            <Text accessibilityRole="alert" style={styles.error}>
              {error}
            </Text>
          ) : null}
          <Pressable
            accessibilityRole="button"
            onPress={publishNote}
            style={styles.button}
          >
            <Text style={styles.buttonText}>发布笔记</Text>
          </Pressable>
          <Text style={styles.hint}>
            这是本地演示：重启或重新加载应用会恢复初始笔记。
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  form: { padding: 20, gap: 12 },
  label: { fontSize: 17, fontWeight: "600", color: "#234536" },
  input: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#FFFCF5",
    color: "#403F36",
    fontSize: 17,
  },
  bodyInput: { minHeight: 180, textAlignVertical: "top" },
  error: { color: "#9B2929", fontSize: 15 },
  button: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#234536",
    alignItems: "center",
  },
  buttonText: { color: "#FFFCF5", fontSize: 17, fontWeight: "600" },
  hint: { fontSize: 14, lineHeight: 22, color: "#615D50" },
});
