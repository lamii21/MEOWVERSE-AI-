import { describe, expect, it } from "vitest";

import { RARITY_VISUALS, getRarityVisual } from "./rarity";

import type { Rarity } from "@/types/analysis";

const ALL_RARITIES: Rarity[] = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"];

describe("rarity visual config", () => {
  it("defines a visual treatment for every rarity value the backend can send", () => {
    for (const rarity of ALL_RARITIES) {
      expect(RARITY_VISUALS[rarity]).toBeDefined();
      expect(RARITY_VISUALS[rarity].cardClassName).toBeTruthy();
      expect(RARITY_VISUALS[rarity].badgeClassName).toBeTruthy();
    }
  });

  it("orders tiers strictly from Common (1) to Mythical (6)", () => {
    const tiers = ALL_RARITIES.map((r) => RARITY_VISUALS[r].tier);
    expect(tiers).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("gives Common a plain treatment and reserves motion for higher tiers", () => {
    expect(RARITY_VISUALS.Common.treatment).toBe("plain");
    expect(RARITY_VISUALS.Legendary.treatment).toBe("aura");
    expect(RARITY_VISUALS.Mythical.treatment).toBe("particles");
  });

  it("falls back to Common for an unrecognized value", () => {
    expect(getRarityVisual("NotARealRarity" as Rarity)).toBe(RARITY_VISUALS.Common);
  });
});
