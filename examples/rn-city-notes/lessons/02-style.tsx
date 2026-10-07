import { StyleSheet, Text, View } from "react-native";

export default function StyleLesson() {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>我的第一张手机页面</Text>
      <Text style={styles.body}>周末去徐汇滨江散步。</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { padding: 24, backgroundColor: "#FFFCF5", borderRadius: 16 },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#234536",
    marginBottom: 12,
  },
  body: { fontSize: 17, lineHeight: 26, color: "#615D50" },
});
