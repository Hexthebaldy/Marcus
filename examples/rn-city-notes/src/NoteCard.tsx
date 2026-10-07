import { Pressable, StyleSheet, Text } from "react-native";
import type { Note } from "./notes";

export function NoteCard({
  note,
  onPress,
}: {
  note: Note;
  onPress: () => void;
}) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.card}>
      <Text style={styles.title}>{note.title}</Text>
      <Text numberOfLines={2} style={styles.body}>
        {note.body}
      </Text>
      <Text style={styles.link}>阅读笔记 →</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { padding: 20, gap: 12, borderRadius: 16, backgroundColor: "#FFFCF5" },
  title: { fontSize: 21, fontWeight: "600", color: "#234536" },
  body: { fontSize: 16, lineHeight: 25, color: "#615D50" },
  link: { color: "#234536", fontSize: 14 },
});
