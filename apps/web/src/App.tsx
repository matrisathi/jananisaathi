import { useEffect, useState } from "react";
import { api, type Staff } from "./api/client";
import { Login } from "./pages/Login";
import { MotherRegister } from "./pages/MotherRegister";
import { PregnancyView } from "./pages/PregnancyView";
import { SessionContext } from "./state/session";

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function AppShell() {
  const [staff, setStaffState] = useState<Staff | null>(null);
  const [checkedSession, setCheckedSession] = useState(false);
  const hash = useHashRoute();

  useEffect(() => {
    // A reload keeps the httpOnly session cookie, so re-check who (if
    // anyone) is signed in rather than assuming a fresh, logged-out state.
    api
      .me()
      .then(setStaffState)
      .catch(() => setStaffState(null))
      .finally(() => setCheckedSession(true));
  }, []);

  function setStaff(next: Staff | null) {
    setStaffState(next);
    if (!next) window.location.hash = "";
  }

  async function handleLogout() {
    await api.logout().catch(() => undefined);
    setStaff(null);
  }

  if (!checkedSession) return <p style={{ fontFamily: "sans-serif" }}>Loading...</p>;

  return (
    <SessionContext.Provider value={{ staff, setStaff }}>
      <div style={{ padding: "2rem" }}>
        {staff ? (
          <>
            <header style={{ marginBottom: 24, fontFamily: "sans-serif" }}>
              Signed in as <strong>{staff.full_name}</strong> ({staff.username}){" "}
              <button onClick={handleLogout}>Log out</button>
              {" | "}
              <a href="#">Find / register mother</a>
            </header>
            {hash.startsWith("#/episodes/") ? (
              <PregnancyView episodeId={hash.replace("#/episodes/", "")} />
            ) : (
              <MotherRegister onEpisodeCreated={(id) => (window.location.hash = `#/episodes/${id}`)} />
            )}
          </>
        ) : (
          <Login />
        )}
      </div>
    </SessionContext.Provider>
  );
}

export function App() {
  return <AppShell />;
}
