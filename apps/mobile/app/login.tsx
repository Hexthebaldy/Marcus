import { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  View,
} from "react-native";
import type { Tokens, User } from "@marcus/api-client";
import { api, useSession } from "../src/session";
import { Screen, styles as s, Field, Button, ErrorMessage, c } from "../src/ui";
export default function Login() {
  const session = useSession();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<string>();
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [showTerms, setShowTerms] = useState(false);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const remaining = Math.max(0, Math.ceil((until - now) / 1000));
  async function send() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await api.post<{
        challenge_id: string;
        resend_after_seconds: number;
      }>("/auth/challenges", {
        email,
        purpose: "login",
        terms_version: "2026-09-v1",
      });
      setChallenge(result.challenge_id);
      setUntil(Date.now() + result.resend_after_seconds * 1000);
      setCode("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function verify() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await api.post<Tokens & { user: User }>("/auth/verify", {
        challenge_id: challenge,
        code,
        device_label: Platform.OS,
        client_type: "mobile",
      });
      await session.login(result, result.user);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Screen>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={{ marginTop: 54, marginBottom: 52, gap: 12 }}>
          <Text style={s.eyebrow}>SHANGHAI · CITY JOURNAL</Text>
          <Text
            style={{
              color: c.green,
              fontSize: 58,
              letterSpacing: -3,
              fontWeight: "800",
            }}
          >
            marcus.
          </Text>
          <Text style={s.heading}>把日常，过成值得记录的一页。</Text>
        </View>
        <View style={{ gap: 16 }}>
          <Text style={s.title}>
            {challenge ? "查收你的邮箱" : "从这里出发"}
          </Text>
          <Text style={s.muted}>
            用邮箱验证码注册或登录，开启你的城市生活。
          </Text>
          <Field
            accessibilityLabel="邮箱"
            value={email}
            onChangeText={(value) => {
              setEmail(value);
              setChallenge(undefined);
            }}
            placeholder="你的邮箱地址"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            editable={!busy}
          />
          <Pressable
            accessibilityRole="checkbox"
            accessibilityState={{ checked: agreed }}
            onPress={() => setAgreed(!agreed)}
            style={s.row}
          >
            <Text style={{ color: c.green, fontSize: 22 }}>
              {agreed ? "☑" : "□"}
            </Text>
            <Text style={s.muted}>我同意本次内测的使用与隐私说明</Text>
          </Pressable>
          <Pressable onPress={() => setShowTerms(!showTerms)}>
            <Text style={{ color: c.green }}>阅读使用与隐私说明</Text>
          </Pressable>
          {showTerms && (
            <View style={s.card}>
              <Text style={s.body}>
                我们使用邮箱验证你的账户，保存你选择公开的笔记、收藏及必要的登录记录。请只发布你有权分享的内容，不公开他人的私人信息。你可以在个人资料中申请注销账户。
              </Text>
              <Text style={s.muted}>
                当前为开发内测版本。正式运营前需补充运营主体、联系方式、完整协议及隐私政策；请勿使用真实敏感资料。
              </Text>
            </View>
          )}
          {challenge && (
            <>
              <Text style={s.muted}>
                验证码发送请求已提交，请检查收件箱和垃圾邮件。
              </Text>
              <Field
                accessibilityLabel="六位验证码"
                value={code}
                onChangeText={setCode}
                placeholder="6 位验证码"
                keyboardType="number-pad"
                textContentType="oneTimeCode"
                maxLength={6}
              />
              <Button
                title="进入 Marcus"
                loading={busy}
                disabled={code.length !== 6 || !agreed}
                onPress={() => void verify()}
              />
            </>
          )}
          <Button
            title={
              remaining
                ? `${remaining} 秒后重发`
                : challenge
                  ? "重新发送验证码"
                  : "获取验证码"
            }
            secondary={!!challenge}
            loading={busy && !challenge}
            disabled={!agreed || !email.trim() || remaining > 0 || busy}
            onPress={() => void send()}
          />
          <ErrorMessage error={error} />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}
