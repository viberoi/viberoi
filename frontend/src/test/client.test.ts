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

  it("GET /sprints/:id/tickets", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ items: [] }), { status: 200 }),
      );
    await api.listTicketsInSprint("sp-uuid");
    expect(String(spy.mock.calls[0]![0])).toBe(
      "/api/sprints/sp-uuid/tickets",
    );
  });

  it("GET /tickets/:id/sessions", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ items: [], next_cursor: null }), {
          status: 200,
        }),
      );
    await api.listSessionsForTicket("t-uuid");
    expect(String(spy.mock.calls[0]![0])).toBe(
      "/api/tickets/t-uuid/sessions",
    );
  });

  it("POST /integrations/:provider/connect", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ authorize_url: "https://x" }), {
        status: 200,
      }),
    );
    await api.connectIntegration("github");
    const [url, init] = spy.mock.calls[0]!;
    expect(String(url)).toBe("/api/integrations/github/connect");
    expect((init as RequestInit).method).toBe("POST");
  });

  it("DELETE /integrations/:provider", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    await api.disconnectIntegration("jira");
    expect((spy.mock.calls[0]![1] as RequestInit).method).toBe("DELETE");
  });

  it("POST /integrations/:provider/sync", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          sync_type: "manual",
          enqueued: true,
          trace_id: "t",
        }),
        { status: 200 },
      ),
    );
    await api.syncIntegration("linear");
    expect(String(spy.mock.calls[0]![0])).toBe(
      "/api/integrations/linear/sync",
    );
  });

  it("POST /notifications/channels sends webhook URL in body", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "x" }), { status: 201 }),
    );
    await api.upsertChannel("slack", "https://hooks.slack.com/services/T/B/X");
    const init = spy.mock.calls[0]![1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      channel: "slack",
      webhook_url: "https://hooks.slack.com/services/T/B/X",
    });
  });

  it("DELETE /notifications/channels/:channel", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    await api.disableChannel("slack");
    expect(String(spy.mock.calls[0]![0])).toBe(
      "/api/notifications/channels/slack",
    );
    expect((spy.mock.calls[0]![1] as RequestInit).method).toBe("DELETE");
  });
});
