export type EditableCreatorProfile = {
  platform: string;
  profile_url: string;
};

export function normalizeCreatorProfile(profile: EditableCreatorProfile): EditableCreatorProfile {
  const value = profile.profile_url.trim();
  if (profile.platform !== "youtube") return { ...profile, profile_url: value };
  if (value.startsWith("@")) {
    return { ...profile, profile_url: `https://www.youtube.com/${value}` };
  }
  if (/^(www\.)?youtube\.com\//i.test(value)) {
    return { ...profile, profile_url: `https://${value}` };
  }
  return { ...profile, profile_url: value };
}
