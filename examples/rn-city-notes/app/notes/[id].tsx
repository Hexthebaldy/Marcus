import { Link, useLocalSearchParams } from "expo-router";
import { ScrollView, StyleSheet, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNotes } from "../../src/notes";

export default function NoteDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { notes } = useNotes();
  // id 来自点卡片时传入的参数；按它找出要显示的那一篇。
  const note = notes.find((candidate) => candidate.id === id);

  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        {note ? (
          <>
            <Text style={styles.title}>{note.title}</Text>
            <Text style={styles.body}>{note.body}</Text>
          </>
        ) : (
          <>
            <Text style={styles.title}>找不到这篇笔记</Text>
            <Text style={styles.body}>
              演示数据只放在内存里，重新加载应用后，新写的笔记会消失。
            </Text>
            <Link href="/" replace style={styles.link}>
              返回首页
            </Link>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  content: { padding: 24, gap: 24 },
  title: { fontSize: 28, fontWeight: "700", color: "#234536" },
  body: { fontSize: 18, lineHeight: 30, color: "#403F36" },
  link: { fontSize: 17, color: "#234536", textDecorationLine: "underline" },
});
