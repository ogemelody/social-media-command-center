# Feature 005 Plan

1. Add `creator_platform_profiles` as a child of the canonical creator.
2. Migrate legacy platform fields into the child table.
3. Merge normalized duplicate creator identities and reassign evidence.
4. Replace the creator API contract with a validated `profiles` collection.
5. Update the creator editor, cards and research drawer.
6. Add contract, duplicate-prevention and migration coverage.
7. Validate the migrated local preview in the browser.

## Architecture decision

Creator identity is provider-neutral. Provider profiles are children of the creator, rather than using a platform account as the creator's primary key. This preserves one research history across platforms and supports later cross-platform analysis without merging provider-native observations.
