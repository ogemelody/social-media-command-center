import { describe, expect, it } from "vitest";
import { normalizeCreatorProfile } from "./creatorProfiles";

describe("normalizeCreatorProfile", () => {
  it("turns a YouTube handle into a complete profile URL", () => {
    expect(
      normalizeCreatorProfile({ platform: "youtube", profile_url: "@KeertiPurswani" }),
    ).toEqual({
      platform: "youtube",
      profile_url: "https://www.youtube.com/@KeertiPurswani",
    });
  });

  it("leaves complete profile URLs intact", () => {
    expect(
      normalizeCreatorProfile({
        platform: "instagram",
        profile_url: "https://www.instagram.com/keerti.purswani/",
      }),
    ).toEqual({
      platform: "instagram",
      profile_url: "https://www.instagram.com/keerti.purswani/",
    });
  });
});
