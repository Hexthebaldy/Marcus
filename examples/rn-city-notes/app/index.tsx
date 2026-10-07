import { router } from "expo-router";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NoteCard } from "../src/NoteCard";
import { useNotes } from "../src/notes";

export default function HomeScreen() {
  const { notes } = useNotes();

  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.page}>
      <FlatList
        data={notes}
        keyExtractor={(note) => note.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.heading}>
            <Text style={styles.title}>把城市里的小发现记下来</Text>
            <Text style={styles.hint}>演出、散步、展览，今天想分享什么？</Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push("/basics")}
              style={styles.lessonLink}
            >
              <Text style={styles.lessonText}>从第一个屏幕开始 →</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              style={styles.button}
              onPress={() => router.push("/compose")}
            >
              <Text style={styles.buttonText}>＋ 写一篇笔记</Text>
            </Pressable>
          </View>
        }
        renderItem={({ item }) => (
          <NoteCard
            note={item}
            onPress={() =>
              router.push({ pathname: "/notes/[id]", params: { id: item.id } })
            }
          />
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  list: { padding: 20, gap: 16 },
  heading: { gap: 12, marginBottom: 8 },
  title: { fontSize: 26, fontWeight: "700", color: "#234536" },
  hint: { fontSize: 15, lineHeight: 24, color: "#615D50" },
  lessonLink: { paddingVertical: 12 },
  lessonText: {
    fontSize: 15,
    color: "#234536",
    textDecorationLine: "underline",
  },
  button: {
    backgroundColor: "#234536",
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  buttonText: { color: "#FFFCF5", fontSize: 17, fontWeight: "600" },
});
