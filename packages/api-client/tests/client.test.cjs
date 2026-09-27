const { test } = require("node:test");
const assert = require("node:assert/strict");
const { ApiClient, ApiError, mediaUrl } = require(
  process.env.MARCUS_TEST_CLIENT,
);

// All requests stay inside a mock transport. These tests complement UI/backend tests.
const expired = { access_token: "test-expired", refresh_token: "test-refresh" };
const renewed = { access_token: "test-renewed", refresh_token: "test-rotated" };
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const unauthorized = () => json({ error: { code: "session_inactive" } }, 401);
function setup(t, handler, clientType = "mobile", initial = expired) {
  const state = { tokens: initial, clears: 0, notifications: 0, calls: [] };
  t.mock.method(globalThis, "fetch", async (url, options) => {
    state.calls.push({ url, options });
    return handler(url, options, state);
  });
  state.client = new ApiClient({
    baseUrl: "https://test.invalid/v1",
    clientType,
    tokenStore: {
      async get() {
        return state.tokens;
      },
      async set(tokens) {
        state.tokens = tokens;
      },
      async clear() {
        state.tokens = null;
        state.clears++;
      },
    },
    onUnauthorized() {
      state.notifications++;
    },
  });
  return state;
}

test("expired access token refreshes and retries the write without losing body or idempotency key", async (t) => {
  const s = setup(t, (url, options) =>
    url.endsWith("/auth/refresh")
      ? json(renewed)
      : options.headers.Authorization === "Bearer test-renewed"
        ? json({ id: "note-1" })
        : unauthorized(),
  );
  const signal = new AbortController().signal;
  assert.deepEqual(
    await s.client.post(
      "/notes",
      { text: "上海散步" },
      { idempotencyKey: "write-1", signal },
    ),
    { id: "note-1" },
  );
  assert.equal(s.calls.length, 3);
  const retry = s.calls[2].options;
  assert.equal(retry.body, JSON.stringify({ text: "上海散步" }));
  assert.equal(retry.headers["Idempotency-Key"], "write-1");
  assert.equal(retry.signal, signal);
  assert.deepEqual(s.tokens, renewed);
  assert.equal(s.calls[1].options.credentials, "omit");
  assert.deepEqual(JSON.parse(s.calls[1].options.body), {
    refresh_token: expired.refresh_token,
  });
});

test("concurrent unauthorized requests share one in-flight refresh", async (t) => {
  let finishRefresh;
  const pendingRefresh = new Promise((resolve) => {
    finishRefresh = resolve;
  });
  let startedRefresh;
  const started = new Promise((resolve) => {
    startedRefresh = resolve;
  });
  const s = setup(t, (url, options) => {
    if (url.endsWith("/auth/refresh")) {
      startedRefresh();
      return pendingRefresh;
    }
    return options.headers.Authorization === "Bearer test-renewed"
      ? json({ ok: true })
      : unauthorized();
  });
  const requests = Promise.all([
    s.client.get("/notes"),
    s.client.get("/editorials"),
    s.client.get("/me"),
  ]);
  await started;
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(
    s.calls.filter((call) => call.url.endsWith("/auth/refresh")).length,
    1,
  );
  finishRefresh(json(renewed));
  assert.deepEqual(await requests, [{ ok: true }, { ok: true }, { ok: true }]);
});

for (const status of [401, 403]) {
  test(`refresh rejected with ${status} clears credentials and reports logout`, async (t) => {
    const s = setup(t, (url) =>
      url.endsWith("/auth/refresh") ? json({}, status) : unauthorized(),
    );
    await assert.rejects(
      s.client.get("/me"),
      (error) => error instanceof ApiError && error.status === 401,
    );
    assert.equal(s.tokens, null);
    assert.equal(s.clears, 1);
    assert.equal(s.notifications, 1);
  });
}

test("temporary refresh server failure preserves credentials and a later request can retry", async (t) => {
  let refreshes = 0;
  const s = setup(t, (url, options) => {
    if (url.endsWith("/auth/refresh"))
      return ++refreshes === 1 ? json({}, 503) : json(renewed);
    return options.headers.Authorization === "Bearer test-renewed"
      ? json({ ok: true })
      : unauthorized();
  });
  await assert.rejects(s.client.get("/me"), ApiError);
  assert.deepEqual(s.tokens, expired);
  assert.equal(s.notifications, 0);
  assert.deepEqual(await s.client.get("/me"), { ok: true });
  assert.equal(refreshes, 2);
});

test("editor refresh uses cookies even without an in-memory token", async (t) => {
  const s = setup(
    t,
    (url) =>
      url.endsWith("/auth/refresh")
        ? json({ access_token: "test-web" })
        : json({ ok: true }),
    "editor_web",
    null,
  );
  assert.equal(await s.client.refresh(), true);
  await s.client.get("/me");
  assert.equal(s.calls[0].options.credentials, "include");
  assert.equal(s.calls[0].options.headers["X-Requested-With"], "Marcus");
  assert.equal(s.calls[0].options.body, "{}");
  assert.equal(s.calls[1].options.credentials, "include");
  assert.equal(s.calls[1].options.headers.Authorization, "Bearer test-web");
});

test("mobile without a refresh token does not make a refresh request", async (t) => {
  const s = setup(t, () => unauthorized(), "mobile", null);
  await assert.rejects(s.client.get("/me"), ApiError);
  assert.equal(s.calls.length, 1);
});

test("authentication failures do not recursively refresh", async (t) => {
  const s = setup(t, () => json({ error: { code: "invalid_code" } }, 401));
  await assert.rejects(
    s.client.post("/auth/verify", {}),
    (error) => error.message === "验证码不正确，请重新输入。",
  );
  assert.equal(s.calls.length, 1);
});

test("a request still unauthorized after refresh stops instead of looping", async (t) => {
  const s = setup(t, (url) =>
    url.endsWith("/auth/refresh") ? json(renewed) : unauthorized(),
  );
  await assert.rejects(s.client.get("/me"), ApiError);
  assert.equal(s.calls.length, 3);
});

test("conflict error preserves user-facing guidance, details and trace ID", async (t) => {
  const s = setup(t, () =>
    json(
      {
        error: {
          code: "version_conflict",
          message: "version_conflict",
          details: { version: 3 },
        },
        request_id: "trace-test",
      },
      409,
    ),
  );
  await assert.rejects(s.client.patch("/notes/n/draft", {}), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 409);
    assert.equal(error.code, "version_conflict");
    assert.match(error.message, /保留本机内容/);
    assert.deepEqual(error.details, { version: 3 });
    assert.equal(error.requestId, "trace-test");
    return true;
  });
});

test("non-JSON server errors show a usable fallback instead of a JSON parser error", async (t) => {
  const s = setup(
    t,
    () => new Response("<html>Bad gateway</html>", { status: 502 }),
  );
  await assert.rejects(
    s.client.get("/notes"),
    (error) =>
      error instanceof ApiError &&
      error.message === "操作未完成，请检查填写内容后重试。",
  );
});

test("query values are encoded, absent values omitted, and 204 responses accepted", async (t) => {
  const s = setup(t, () => new Response(null, { status: 204 }));
  assert.equal(
    await s.client.get("/search", {
      q: "上海 & 展览",
      page: 0,
      city: null,
      cursor: undefined,
    }),
    undefined,
  );
  const query = new URL(s.calls[0].url).searchParams;
  assert.equal(query.get("q"), "上海 & 展览");
  assert.equal(query.get("page"), "0");
  assert.equal(query.has("city"), false);
  assert.equal(query.has("cursor"), false);
});

test("media URL uses the requested size without substituting another missing variant", () => {
  const asset = {
    variants: {
      thumb: { url: "https://test.invalid/thumb" },
      detail: { url: "https://test.invalid/detail" },
    },
  };
  assert.equal(mediaUrl(asset, "thumb"), "https://test.invalid/thumb");
  assert.equal(mediaUrl(asset, "detail"), "https://test.invalid/detail");
  assert.equal(mediaUrl(asset), undefined);
  assert.equal(mediaUrl(null), undefined);
});
