import { useState } from "react";
import { Alert, Pressable, Text, View } from "react-native";
import type { Reactions } from "@marcus/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "./session";
import { styles as s, c, ErrorMessage, Field, Button } from "./ui";
export function ContentActions({
  kind,
  id,
  versionId,
  reactions,
  authorId,
  onBlocked,
}: {
  kind: "notes" | "editorials";
  id: string;
  versionId: string;
  reactions: Reactions;
  authorId?: string;
  onBlocked?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [report, setReport] = useState(false);
  const [reason, setReason] = useState("");
  const queryClient = useQueryClient();
  async function toggle(action: "like" | "bookmark") {
    setBusy(true);
    setError(undefined);
    try {
      const active = action === "like" ? reactions.liked : reactions.bookmarked;
      if (active) await api.delete(`/${kind}/${id}/reactions/${action}`);
      else await api.put(`/${kind}/${id}/reactions/${action}`);
      await queryClient.invalidateQueries();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function submitReport() {
    setBusy(true);
    setError(undefined);
    try {
      await api.post(`/${kind}/${id}/reports`, {
        [kind === "notes" ? "submission_id" : "revision_id"]: versionId,
        reason: "other",
        description: reason,
      });
      setReport(false);
      Alert.alert("举报已提交", "我们会核实你反馈的内容。");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function block() {
    Alert.alert("屏蔽这位作者？", "之后将不再显示这位作者的内容。", [
      { text: "取消", style: "cancel" },
      {
        text: "屏蔽",
        style: "destructive",
        onPress: () => {
          void api
            .put(`/users/${authorId}/block`)
            .then(async () => {
              await queryClient.invalidateQueries();
              onBlocked?.();
            })
            .catch(setError);
        },
      },
    ]);
  }
  return (
    <View style={{ gap: 14, paddingVertical: 20 }}>
      <View style={s.rule} />
      <View style={{ ...s.row, justifyContent: "space-between" }}>
        <Pressable disabled={busy} onPress={() => void toggle("like")}>
          <Text style={{ color: c.green, padding: 8 }}>
            {reactions.liked ? "♥" : "♡"} {reactions.like_count ?? 0}
          </Text>
        </Pressable>
        <Pressable disabled={busy} onPress={() => void toggle("bookmark")}>
          <Text style={{ color: c.green, padding: 8 }}>
            {reactions.bookmarked ? "★ 已收藏" : "☆ 收藏"}
          </Text>
        </Pressable>
        <Pressable onPress={() => setReport(!report)}>
          <Text style={s.muted}>举报</Text>
        </Pressable>
        {authorId && (
          <Pressable onPress={block}>
            <Text style={s.muted}>屏蔽</Text>
          </Pressable>
        )}
      </View>
      {report && (
        <>
          <Field
            value={reason}
            onChangeText={setReason}
            placeholder="请描述问题，帮助我们核实"
            multiline
            maxLength={1000}
          />
          <Button
            title="提交举报"
            disabled={!reason.trim()}
            loading={busy}
            onPress={() => void submitReport()}
          />
        </>
      )}
      <ErrorMessage error={error} />
    </View>
  );
}
