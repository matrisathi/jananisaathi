import { useEffect, useState } from "react";
import { api, ApiError, type PregnancyEpisode } from "../api/client";

export function PregnancyView({ episodeId }: { episodeId: string }) {
  const [episode, setEpisode] = useState<PregnancyEpisode | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEpisode(null);
    setError(null);
    // Always fetched fresh from the API by id in the URL — nothing about
    // this view depends on in-memory state carried over from creation, so
    // a full page reload still shows the persisted record, not a stale copy.
    api
      .getPregnancyEpisode(episodeId)
      .then((e) => {
        if (!cancelled) setEpisode(e);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load record");
      });
    return () => {
      cancelled = true;
    };
  }, [episodeId]);

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!episode) return <p>Loading...</p>;

  return (
    <div style={{ maxWidth: 480, fontFamily: "sans-serif" }}>
      <h2>Pregnancy episode (persisted record)</h2>
      <dl>
        <dt>Mother</dt>
        <dd>{episode.mother_full_name}</dd>
        <dt>Status</dt>
        <dd>{episode.status}</dd>
        <dt>Dating source</dt>
        <dd>{episode.dating_source}</dd>
        <dt>Episode id</dt>
        <dd style={{ fontFamily: "monospace" }}>{episode.id}</dd>
        <dt>Created</dt>
        <dd>{new Date(episode.created_at).toLocaleString()}</dd>
      </dl>
      <p style={{ fontSize: 12, color: "#777" }}>
        Reload this page — the record above is re-fetched from the API each time, not kept only in
        the browser.
      </p>
    </div>
  );
}
