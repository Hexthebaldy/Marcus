import { Image, StyleSheet, Text, View } from "react-native";

export default function ImageLesson() {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>我的第一张手机页面</Text>
      <Text style={styles.body}>周末去徐汇滨江散步。</Text>
      <Image
        source={require("../assets/react-native-icon.png")}
        style={styles.image}
        resizeMode="contain"
        accessibilityLabel="React Native 图标"
      />
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
  image: { width: 120, height: 120, marginTop: 20 },
});
