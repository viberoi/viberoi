import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";

const STORAGE_KEY = "viberoi.dev_user";

beforeEach(() => {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      email: "alice@acme.test",
      developerId: "dev-1",
      orgId: "org-1",
      role: "OrgAdmin",
      teamId: null,
    }),
  );
});

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("attaches the dev headers on every request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ window_days: 30 }), { status: 200 }),
    );
    await api.kpiSnapshot(30);
    expect(fetchSpy).toHaveBeenCalledOnce();
    const [, init] = fetchSpy.mock.calls[0]!;
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["X-Dev-Org-Id"]).toBe("org-1");
    expect(headers["X-Dev-Role"]).toBe("OrgAdmin");
    expect(headers["X-Dev-Developer-Id"]).toBe("dev-1");
    expect(headers["X-Dev-Team-Id"]).toBeUndefined();
  });

  it("throws ApiError with the response status on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "nope" }), { status: 401 }),
    );
    await expect(api.kpiSnapshot()).rejects.toBeInstanceOf(ApiError);
  });

  it("appends cursor + limit to /sessions", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], next_cursor: null }), {
        status: 200,
      }),
    );
    await api.listSessions("abc123", 10);
    const [url] = fetchSpy.mock.calls[0]!;
    expect(String(url)).toBe("/api/sessions?cursor=abc123&limit=10");
  });

  it("GET /sessions/:id", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    await api.getSession("sess-uuid");
    expect(String(spy.mock.calls[0]![0])).toBe("/api/sessions/sess-uuid");
  });

  it("/sprints with no states omits query string", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ items: [] }), { status: 200 }),
      );
    await api.listSprints();
    expect(String(spy.mock.calls[0]![0])).toBe("/api/sprints");
  });

  it("/sprints repeats state per filter", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ items: [] }), { status: 200 }),
      );
    await api.listSprints(["active", "future"]);
    expect(String(spy.mock.calls[0]![0])).toBe(
      "/api/sprints?state=active&state=future",
    );
  });

  it("GET /sprints/:id", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    await api.getSprint("sp-uuid");
    expect(String(spy.mock.calls[0]![0])).toBe("/api/sprints/sp-uuid");
  });

  it("GET /tickets/:id", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    await api.getTicket("t-uuid");
    expect(String(spy.mock.calls[0]![0])).toBe("/api/tickets/t-uuid");
  });

  it("GET /developers/me", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    await api.me();
    expect(String(spy.mock.calls[0]![0])).toBe("/api/developers/me");
  });
});
