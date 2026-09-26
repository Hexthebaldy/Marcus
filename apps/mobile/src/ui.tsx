import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors as c } from "@marcus/design-tokens";
export { c };
export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: c.background },
  page: { padding: 22, paddingBottom: 36, gap: 18 },
  title: {
    fontSize: 32,
    lineHeight: 39,
    fontWeight: "700",
    color: c.ink,
    letterSpacing: -1,
  },
  heading: { fontSize: 21, fontWeight: "600", color: c.ink, lineHeight: 30 },
  body: { fontSize: 16, color: c.ink, lineHeight: 27 },
  muted: { fontSize: 13, color: c.muted, lineHeight: 21 },
  eyebrow: {
    fontSize: 11,
    color: c.green,
    fontWeight: "700",
    letterSpacing: 2,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  card: { backgroundColor: c.paper, borderRadius: 12, padding: 18, gap: 10 },
  input: {
    backgroundColor: c.paper,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: c.line,
    padding: 14,
    fontSize: 16,
    color: c.ink,
  },
  rule: { height: 1, backgroundColor: c.line },
});
export function Screen({
  children,
  scroll = true,
}: React.PropsWithChildren<{ scroll?: boolean }>) {
  return (
    <SafeAreaView edges={["top", "left", "right"]} style={styles.screen}>
      {scroll ? (
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.page}
        >
          {children}
        </ScrollView>
      ) : (
        children
      )}
    </SafeAreaView>
  );
}
export function Button({
  title,
  onPress,
  loading,
  disabled,
  secondary,
  style,
}: {
  title: string;
  onPress(): void;
  loading?: boolean;
  disabled?: boolean;
  secondary?: boolean;
  style?: ViewStyle;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading }}
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        {
          backgroundColor: secondary ? c.khaki : c.green,
          borderRadius: 10,
          minHeight: 48,
          padding: 13,
          alignItems: "center",
          justifyContent: "center",
          opacity: disabled || loading ? 0.5 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? c.green : c.paper} />
      ) : (
        <Text
          style={{
            color: secondary ? c.green : c.paper,
            fontSize: 15,
            fontWeight: "600",
          }}
        >
          {title}
        </Text>
      )}
    </Pressable>
  );
}
export function Field(props: TextInputProps) {
  return (
    <TextInput
      placeholderTextColor={c.muted}
      {...props}
      style={[styles.input, props.style]}
    />
  );
}
export function ErrorMessage({ error }: { error?: unknown }) {
  return error ? (
    <Text
      accessibilityRole="alert"
      style={{ color: c.error, fontSize: 14, lineHeight: 22 }}
    >
      {error instanceof Error ? error.message : String(error)}
    </Text>
  ) : null;
}
export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <View style={{ paddingVertical: 52, gap: 12 }}>
      <Text style={styles.heading}>{title}</Text>
      <Text style={styles.muted}>{body}</Text>
    </View>
  );
}
export function Busy() {
  return <ActivityIndicator style={{ padding: 40 }} color={c.green} />;
}
export const date = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "时间待公布";
