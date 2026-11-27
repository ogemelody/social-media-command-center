# Feature 006 Plan

1. Extend the YouTube provider with direct channel resolution, batched public video details and bounded comment retrieval.
2. Add creator research runs, public creator videos and public comments as provider-native entities.
3. Implement a synchronous manual refresh service with token refresh, idempotent upserts, quota accounting and partial comment failure handling.
4. Add authenticated refresh and research-summary endpoints.
5. Extend the creator drawer with a content-performance view and audience-question evidence.
6. Add provider, API and UI quality checks.

## Architecture decisions

- Reuse the owner's read-only YouTube OAuth connection instead of adding a second credential path.
- Cache resolved channel IDs and uploads playlist IDs on the YouTube platform profile.
- Use a 20-video window and comments for only the top five videos; this is a research sample, not a channel archive.
- Compute `relative_view_ratio = views / median_views` over available synchronized videos. `breakout` means at least 2.0× that baseline and is explicitly a derived interpretation.
- Estimate quota from completed list requests. The value is operational telemetry, not Google's billing record.
