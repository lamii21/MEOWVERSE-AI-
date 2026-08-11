import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchPublicStory, generateStory, shareStory, StoryApiError } from "./stories";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const sampleStory = {
  id: "story-1",
  analysis_id: "analysis-1",
  style: "magical_adventure",
  story: {
    title: "t",
    subtitle: "s",
    opening: "o",
    chapters: [{ chapter_number: 1, title: "c", text: "x" }],
    ending: "e",
    moral: "m",
    quote: "q",
  },
  story_mode: "demo",
  provider: "demo",
  is_public: false,
  created_at: "2026-08-10T12:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateStory", () => {
  it("posts style and regenerate, returns the parsed story on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, sampleStory));
    vi.stubGlobal("fetch", fetchMock);

    const result = await generateStory("analysis-1", "magical_adventure", true);

    expect(result.id).toBe("story-1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/analyses/analysis-1/story");
    expect(JSON.parse(init.body)).toEqual({ style: "magical_adventure", regenerate: true });
  });

  it("throws a not_found StoryApiError on 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(404, { detail: "nope" })));

    await expect(generateStory("missing", "magical_adventure")).rejects.toMatchObject({
      kind: "not_found",
    });
  });

  it("throws a validation StoryApiError on 422 using the server detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(422, { detail: "That style isn't real." })),
    );

    await expect(generateStory("analysis-1", "magical_adventure")).rejects.toMatchObject({
      kind: "validation",
      message: "That style isn't real.",
    });
  });

  it("throws a rate_limited StoryApiError on 429", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(429, {})));

    await expect(generateStory("analysis-1", "magical_adventure")).rejects.toMatchObject({
      kind: "rate_limited",
    });
  });

  it("throws a network StoryApiError when fetch itself rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    await expect(generateStory("analysis-1", "magical_adventure")).rejects.toBeInstanceOf(
      StoryApiError,
    );
    await expect(generateStory("analysis-1", "magical_adventure")).rejects.toMatchObject({
      kind: "network",
    });
  });
});

describe("fetchPublicStory", () => {
  it("returns the story on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, sampleStory)));

    const result = await fetchPublicStory("story-1");

    expect(result.id).toBe("story-1");
  });

  it("throws not_found for a private or missing story", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(404, {})));

    await expect(fetchPublicStory("story-1")).rejects.toMatchObject({ kind: "not_found" });
  });
});

describe("shareStory", () => {
  it("posts to the share endpoint and returns the updated story", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { ...sampleStory, is_public: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await shareStory("story-1");

    expect(result.is_public).toBe(true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/stories/story-1/share");
    expect(init.method).toBe("POST");
  });
});
