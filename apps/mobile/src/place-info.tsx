import { useState } from "react";
import { Linking, Text, View } from "react-native";
import type { Place, CityEvent } from "@marcus/api-client";
import { api } from "./session";
import { Button, ErrorMessage, styles as s, date } from "./ui";
export function PlaceInfo({ place }: { place: Place }) {
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>到访信息 · {place.district?.name}</Text>
      <Text style={s.heading}>{place.name}</Text>
      {place.status !== "active" && (
        <Text style={s.muted}>该地点已关闭，请留意最新消息。</Text>
      )}
      <Text style={s.body}>{place.address}</Text>
      {!!place.opening_hours_text && (
        <Text style={s.muted}>营业时间 · {place.opening_hours_text}</Text>
      )}
      {!!place.transport_notes && (
        <Text style={s.muted}>{place.transport_notes}</Text>
      )}
    </View>
  );
}
export function EventInfo({ event }: { event: CityEvent }) {
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function mark(state: "interested" | "attended" | null) {
    setBusy(true);
    setError(undefined);
    try {
      if (state)
        await api.put(`/events/${event.id}/participation`, {
          state,
          session_id: null,
          attended_at: state === "attended" ? new Date().toISOString() : null,
        });
      else await api.delete(`/events/${event.id}/participation`);
      setMessage(
        state === "interested"
          ? "已标记想去"
          : state === "attended"
            ? "已记录参与"
            : "已取消标记",
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const price =
    event.price?.status === "unknown" || event.price?.min_fen == null
      ? "票价待公布"
      : event.price.min_fen === 0 && !event.price.max_fen
        ? "免费"
        : `¥${event.price.min_fen / 100}${event.price.max_fen && event.price.max_fen !== event.price.min_fen ? `–${event.price.max_fen / 100}` : ""}`;
  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>活动指南</Text>
      <Text style={s.heading}>{event.title}</Text>
      <Text style={s.body}>{price}</Text>
      {event.status !== "published" && (
        <Text style={s.muted}>
          {event.status === "cancelled" ? "活动已取消" : "活动已结束"}
        </Text>
      )}
      {event.upcoming_sessions?.map((session) => (
        <Text key={session.id} style={s.muted}>
          {date(session.starts_at)} {session.entry_note}
        </Text>
      ))}
      {!event.place && <Text style={s.muted}>场地待确认</Text>}
      {event.booking_url && /^https?:\/\//.test(event.booking_url) && (
        <Button
          secondary
          title="查看预约信息 ↗"
          onPress={() =>
            void Linking.openURL(event.booking_url!).catch(setError)
          }
        />
      )}
      <View style={s.row}>
        <Button
          title="想去"
          disabled={busy}
          onPress={() => void mark("interested")}
          style={{ flex: 1 }}
        />
        <Button
          secondary
          title="去过"
          disabled={busy}
          onPress={() => void mark("attended")}
          style={{ flex: 1 }}
        />
      </View>
      <Button
        secondary
        title="取消参与标记"
        disabled={busy}
        onPress={() => void mark(null)}
      />
      {!!message && <Text style={s.muted}>{message}</Text>}
      <ErrorMessage error={error} />
    </View>
  );
}
