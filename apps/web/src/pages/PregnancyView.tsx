import { useEffect, useState } from "react";
import { api, ApiError, type Person, type PregnancyEpisode } from "../api/client";
import { formatAge } from "../lib/age";

export function PregnancyView({ episodeId }: { episodeId: string }) {
  const [episode, setEpisode] = useState<PregnancyEpisode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mother, setMother] = useState<Person | null>(null);
  const [motherError, setMotherError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setEpisode(null);
    setError(null);
    setMother(null);
    setMotherError(null);
    // Always fetched fresh from the API by id in the URL — nothing about
    // this view depends on in-memory state carried over from creation, so
    // a full page reload still shows the persisted record, not a stale copy.
    api
      .getPregnancyEpisode(episodeId)
      .then((e) => {
        if (cancelled) return;
        setEpisode(e);
        return api
          .getPerson(e.mother_person_id)
          .then((p) => {
            if (!cancelled) setMother(p);
          })
          .catch((err) => {
            if (!cancelled) {
              setMotherError(err instanceof ApiError ? err.message : "Could not load mother's record");
            }
          });
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load record");
      });
    return () => {
      cancelled = true;
    };
  }, [episodeId]);

  async function handleVerify() {
    if (!mother) return;
    setVerifying(true);
    try {
      const updated = await api.verifyContact(mother.id);
      setMother(updated);
    } catch (err) {
      setMotherError(err instanceof ApiError ? err.message : "Could not verify contact");
    } finally {
      setVerifying(false);
    }
  }

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

      <h3>Mother's record</h3>
      {motherError && <p style={{ color: "crimson" }}>{motherError}</p>}
      {!mother && !motherError && <p>Loading mother's record...</p>}
      {mother && (
        <dl>
          <dt>Age / DOB</dt>
          <dd>{formatAge(mother)}</dd>
          <dt>Reported medical history</dt>
          <dd>{mother.reported_medical_history || "None recorded"}</dd>
          <dt>Known allergies / medicines</dt>
          <dd>{mother.known_allergies_medicines || "None recorded"}</dd>
          <dt>Contact ({mother.phone})</dt>
          <dd>
            {mother.contact_verified_at ? (
              <>
                Confirmed by {mother.contact_verified_by_name ?? "a staff member"} on{" "}
                {new Date(mother.contact_verified_at).toLocaleString()}
              </>
            ) : (
              <>
                Not yet confirmed with the family (staff attestation only — no OTP in this system){" "}
                <button onClick={handleVerify} disabled={verifying}>
                  {verifying ? "Confirming..." : "Confirm this is their number"}
                </button>
              </>
            )}
          </dd>
        </dl>
      )}

      <p style={{ fontSize: 12, color: "#777" }}>
        Reload this page — the record above is re-fetched from the API each time, not kept only in
        the browser.
      </p>
    </div>
  );
}
