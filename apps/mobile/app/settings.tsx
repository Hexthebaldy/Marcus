import { useState } from "react";
import { Alert, Text } from "react-native";
import { router } from "expo-router";
import { api, useSession } from "../src/session";
import { pickAndUpload } from "../src/upload";
import { Button, ErrorMessage, Field, Screen, styles as s } from "../src/ui";
export default function Settings() {
  const { user, reload } = useSession();
  const [name, setName] = useState(user?.display_name ?? "");
  const [bio, setBio] = useState(user?.bio ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<string>();
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      await api.patch("/me", { display_name: name, bio });
      await reload();
      setMessage("个人资料已保存。");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function avatar() {
    setBusy(true);
    setError(undefined);
    try {
      const values = await pickAndUpload("avatar", 1, setMessage);
      if (values[0]) {
        if (values[0].status !== "ready")
          throw new Error("照片还在处理，请稍后重新选择。");
        await api.patch("/me", { avatar_asset_id: values[0].id });
        await reload();
        setMessage("头像已更新。");
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function requestDeletion() {
    setBusy(true);
    setError(undefined);
    try {
      const response = await api.post<{ challenge_id: string }>(
        "/auth/challenges",
        { purpose: "delete_account", email },
      );
      setChallenge(response.challenge_id);
      setMessage("注销验证码已提交发送，请检查邮箱。");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function confirmDeletion() {
    Alert.alert(
      "确认注销账户？",
      "账户将立即停用并撤销所有登录，随后清理相关数据。此操作无法在应用中撤销。",
      [
        { text: "取消", style: "cancel" },
        {
          text: "确认注销",
          style: "destructive",
          onPress: () => {
            setBusy(true);
            void api
              .delete("/me", { challenge_id: challenge, code })
              .then(async () => {
                await reload();
                router.replace("/login");
              })
              .catch(setError)
              .finally(() => setBusy(false));
          },
        },
      ],
    );
  }
  return (
    <Screen>
      <Text style={s.heading}>关于你</Text>
      <Field
        accessibilityLabel="昵称"
        placeholder="昵称"
        value={name}
        onChangeText={setName}
        maxLength={40}
      />
      <Field
        accessibilityLabel="简介"
        placeholder="写一句自我介绍"
        multiline
        value={bio}
        onChangeText={setBio}
        maxLength={300}
      />
      <Button
        secondary
        title="更换头像"
        disabled={busy}
        onPress={() => void avatar()}
      />
      <Button
        title="保存资料"
        loading={busy}
        disabled={!name.trim()}
        onPress={() => void save()}
      />
      <Text style={s.muted}>{message}</Text>
      <ErrorMessage error={error} />
      <Button
        secondary
        title={deleting ? "取消注销申请" : "注销账户"}
        disabled={busy}
        onPress={() => setDeleting(!deleting)}
      />
      {deleting && (
        <>
          <Text style={s.muted}>请填写注册邮箱，验证后再确认注销。</Text>
          <Field
            placeholder="注册邮箱"
            value={email}
            onChangeText={(value) => {
              setEmail(value);
              setChallenge(undefined);
            }}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <Button
            secondary
            title="发送注销验证码"
            disabled={busy || !email.trim()}
            onPress={() => void requestDeletion()}
          />
          {challenge && (
            <>
              <Field
                placeholder="六位验证码"
                value={code}
                onChangeText={setCode}
                keyboardType="number-pad"
                maxLength={6}
              />
              <Button
                title="验证并注销"
                disabled={busy || code.length !== 6}
                onPress={confirmDeletion}
              />
            </>
          )}
        </>
      )}
    </Screen>
  );
}
