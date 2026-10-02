import { useState } from "react";
import { FindMother } from "./FindMother";
import { RegisterNewMother } from "./RegisterNewMother";

type Mode = "find" | "register";

export function MotherRegister({ onEpisodeCreated }: { onEpisodeCreated: (episodeId: string) => void }) {
  const [mode, setMode] = useState<Mode>("find");

  return (
    <div style={{ fontFamily: "sans-serif" }}>
      <div role="tablist" style={{ marginBottom: 16 }}>
        <button
          role="tab"
          aria-selected={mode === "find"}
          onClick={() => setMode("find")}
          style={{ fontWeight: mode === "find" ? "bold" : "normal" }}
        >
          Find existing mother
        </button>{" "}
        <button
          role="tab"
          aria-selected={mode === "register"}
          onClick={() => setMode("register")}
          style={{ fontWeight: mode === "register" ? "bold" : "normal" }}
        >
          Register new mother
        </button>
      </div>
      {mode === "find" ? (
        <FindMother onEpisodeCreated={onEpisodeCreated} />
      ) : (
        <RegisterNewMother onEpisodeCreated={onEpisodeCreated} />
      )}
    </div>
  );
}
