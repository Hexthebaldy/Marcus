import { useEffect, useState, type FormEvent } from "react";
import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { City, Page, Tokens, User } from "@marcus/api-client";
import { api, tokenStore } from "./api";
import { ErrorBox, Field, SessionContext } from "./shared";
import { ArticleList, ArticleEditor } from "./Articles";
import { Catalog } from "./Catalog";
import { Moderation, AccessManagement } from "./Moderation";
function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState("");
  const [remaining, setRemaining] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [agreed, setAgreed] = useState(false);
  useEffect(() => {
    const interval = setInterval(
      () => setRemaining((value) => Math.max(0, value - 1)),
      1000,
    );
    return () => clearInterval(interval);
  }, []);
  const send = async () => {
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
      setRemaining(result.resend_after_seconds);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  const verify = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const result = await api.post<Tokens & { user: User }>("/auth/verify", {
        challenge_id: challenge,
        code,
        device_label: "Marcus 编辑后台",
        client_type: "editor_web",
      });
      await tokenStore.set(result);
      onLogin(result.user);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="login">
      <section className="login-story">
        <div className="brand">
          marcus<span>城市编辑室</span>
        </div>
        <p className="eyebrow">SHANGHAI, THROUGH YOUR EYES</p>
        <h1>
          把这座城市，
          <br />
          写得值得出发。
        </h1>
        <p>
          记录一个地方的性格，
          <br />
          发现一场活动的不同。
        </p>
        <span className="edition">SHANGHAI EDITION / 01</span>
      </section>
      <section className="login-form">
        <h2>欢迎回到编辑室</h2>
        <p>使用邮箱验证码登录。后台功能需要编辑或审核权限。</p>
        <form onSubmit={verify}>
          <Field label="邮箱地址">
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setChallenge("");
              }}
              placeholder="you@example.com"
            />
          </Field>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(event) => setAgreed(event.target.checked)}
            />
            我同意{" "}
            <a href="/terms" target="_blank">
              使用说明
            </a>{" "}
            与{" "}
            <a href="/privacy" target="_blank">
              隐私说明
            </a>
          </label>
          <button
            className="secondary"
            type="button"
            disabled={!email || !agreed || busy || remaining > 0}
            onClick={() => void send()}
          >
            {remaining ? `${remaining} 秒后可重新发送` : "发送验证码"}
          </button>
          {challenge && (
            <>
              <p className="notice">
                已提交发送至你填写的邮箱，请同时检查垃圾邮件。
              </p>
              <Field label="六位验证码">
                <input
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  maxLength={6}
                  required
                />
              </Field>
              <button
                className="primary"
                disabled={busy || code.length !== 6 || !agreed}
              >
                进入编辑室
              </button>
            </>
          )}
          <ErrorBox error={error} />
        </form>
      </section>
    </main>
  );
}
export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [logoutError, setLogoutError] = useState<unknown>(null);
  const queryClient = useQueryClient();
  useEffect(() => {
    let active = true;
    void api
      .refresh()
      .then((ok) => (ok ? api.get<User>("/me") : null))
      .then((value) => {
        if (active) setUser(value);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    const logout = () => {
      setUser(null);
      queryClient.clear();
    };
    window.addEventListener("marcus:unauthorized", logout);
    return () => {
      active = false;
      window.removeEventListener("marcus:unauthorized", logout);
    };
  }, [queryClient]);
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: () =>
      api.get<Page<City>>("/cities").then((result) => result.items),
    enabled: Boolean(user),
  });
  const logout = async () => {
    try {
      setLogoutError(null);
      await api.post("/auth/logout");
      await tokenStore.clear();
      queryClient.clear();
      setUser(null);
    } catch (error) {
      setLogoutError(error);
    }
  };
  if (
    window.location.pathname === "/terms" ||
    window.location.pathname === "/privacy"
  )
    return (
      <main className="legal">
        <h1>
          {window.location.pathname === "/terms" ? "使用说明" : "隐私说明"}
        </h1>
        <p>
          Marcus
          用于发现城市活动与地点、发布生活笔记。请发布你有权使用的内容，不发布违法、侵权、骚扰或虚假资料。
        </p>
        <p>
          邮箱用于验证账户与发送验证码；资料、内容、互动和必要的安全记录用于提供服务。私有草稿仅向作者及有权进行该次审核的人员开放。你可以在手机个人页面申请注销账户。
        </p>
        <p>
          当前为开发版本，请勿向此环境提交生产用户资料。正式运营前需要补充运营主体、联系方式、数据保留政策与适用条款。
        </p>
        <a href="/">返回编辑室</a>
      </main>
    );
  if (loading)
    return (
      <div className="boot">
        marcus <small>正在恢复登录…</small>
      </div>
    );
  if (!user) return <Login onLogin={setUser} />;
  const canEdit = user.roles.some((role) => ["editor", "admin"].includes(role));
  const canReview = user.roles.some((role) =>
    ["moderator", "admin"].includes(role),
  );
  if (!canEdit && !canReview)
    return (
      <main className="legal">
        <h1>账户已登录</h1>
        <p>此账户尚未获授编辑或审核权限，请联系管理员。</p>
        <button onClick={() => void logout()}>退出登录</button>
        <ErrorBox error={logoutError} />
      </main>
    );
  if (!cities.data?.[0])
    return (
      <main className="legal">
        <p>正在加载城市资料…</p>
        <ErrorBox error={cities.error} />
        <button onClick={() => void cities.refetch()}>重试</button>
      </main>
    );
  return (
    <SessionContext.Provider value={{ user, city: cities.data[0] }}>
      <div className="shell">
        <aside className="sidebar">
          <NavLink to="/" className="brand">
            marcus<span>城市编辑室</span>
          </NavLink>
          <p className="sidebar-city">SHANGHAI / 上海</p>
          <nav>
            {canEdit && (
              <>
                <NavLink to="/articles">
                  编辑文章<span>Editorial</span>
                </NavLink>
                <NavLink to="/places">
                  地点资料<span>Places</span>
                </NavLink>
                <NavLink to="/events">
                  活动资料<span>Events</span>
                </NavLink>
                <NavLink to="/tags">
                  内容标签<span>Tags</span>
                </NavLink>
              </>
            )}
            {canReview && (
              <>
                <NavLink to="/reviews">
                  内容审核<span>Review</span>
                </NavLink>
                <NavLink to="/reports">
                  用户举报<span>Reports</span>
                </NavLink>
              </>
            )}
            {user.roles.includes("admin") && (
              <NavLink to="/access">
                人员权限<span>Access</span>
              </NavLink>
            )}
          </nav>
          <div className="sidebar-foot">
            <strong>{user.display_name}</strong>
            <small>{user.roles.join(" / ")}</small>
            <button onClick={() => void logout()}>退出登录 ↗</button>
            <ErrorBox error={logoutError} />
          </div>
        </aside>
        <main className="workspace">
          <Routes>
            <Route
              path="/"
              element={
                <Navigate to={canEdit ? "/articles" : "/reviews"} replace />
              }
            />
            {canEdit && (
              <>
                <Route path="/articles" element={<ArticleList />} />
                <Route path="/articles/:id" element={<ArticleEditor />} />
                <Route path="/places" element={<Catalog kind="places" />} />
                <Route path="/events" element={<Catalog kind="events" />} />
                <Route path="/tags" element={<Catalog kind="tags" />} />
              </>
            )}
            {canReview && (
              <>
                <Route
                  path="/reviews"
                  element={<Moderation mode="reviews" />}
                />
                <Route
                  path="/reports"
                  element={<Moderation mode="reports" />}
                />
              </>
            )}
            {user.roles.includes("admin") && (
              <Route path="/access" element={<AccessManagement />} />
            )}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </SessionContext.Provider>
  );
}
