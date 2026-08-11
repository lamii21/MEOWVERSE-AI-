import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  _resetForTests,
  dismissCurrent,
  getSnapshot,
  pushGamificationEvent,
  subscribe,
} from "./discovery-toast-store";

import type { GamificationEvent } from "@/types/gamification";

function makeEvent(overrides: Partial<GamificationEvent> = {}): GamificationEvent {
  return {
    xp_awarded: 100,
    total_xp: 100,
    level: 1,
    leveled_up: false,
    is_new_breed: false,
    is_new_rarity: false,
    newly_unlocked: [],
    ...overrides,
  };
}

beforeEach(() => {
  _resetForTests();
});

describe("discovery-toast-store", () => {
  it("does nothing for a null or empty event", () => {
    pushGamificationEvent(null);
    expect(getSnapshot()).toBeNull();

    pushGamificationEvent(makeEvent());
    expect(getSnapshot()).toBeNull();
  });

  it("shows a breed-discovery toast", () => {
    pushGamificationEvent(makeEvent({ is_new_breed: true }));
    expect(getSnapshot()?.kind).toBe("breed");
  });

  it("queues multiple discoveries from one event and shows them one at a time", () => {
    pushGamificationEvent(
      makeEvent({
        is_new_breed: true,
        is_new_rarity: true,
        leveled_up: true,
        newly_unlocked: [
          {
            key: "first_meow",
            emoji: "🐾",
            label: "First Paw",
            description: "Discover your first cat.",
            unlocked: true,
            unlocked_at: "2026-01-01T00:00:00Z",
            progress_current: 1,
            progress_target: 1,
          },
        ],
      }),
    );

    const seen: string[] = [];
    const first = getSnapshot();
    expect(first).not.toBeNull();
    seen.push(first!.kind);

    dismissCurrent();
    seen.push(getSnapshot()!.kind);
    dismissCurrent();
    seen.push(getSnapshot()!.kind);
    dismissCurrent();
    seen.push(getSnapshot()!.kind);

    expect(seen).toEqual(["breed", "rarity", "achievement", "levelup"]);

    dismissCurrent();
    expect(getSnapshot()).toBeNull();
  });

  it("notifies subscribers when the current toast changes", () => {
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);

    pushGamificationEvent(makeEvent({ is_new_breed: true }));
    expect(listener).toHaveBeenCalled();

    unsubscribe();
  });
});
