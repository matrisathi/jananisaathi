import { useMutation } from "@tanstack/react-query";
import { HeartPulse, KeyRound, LogOut } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { api, ApiError } from "../api/client";
import { Button } from "../components/ui/button";
import { Field, Input } from "../components/ui/field";
import { Alert } from "../components/ui/status";
import { passwordProblem } from "../lib/password";
import { useSession } from "../state/session";

/** First sign-in with an admin-issued temporary password: the person chooses
 * their own before anything else (the server refuses other requests). */
export function SetPassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { staff, setStaff, signOut } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const change = useMutation({
    mutationFn: () => api.changePassword(current, next),
    meta: { toast: t("setPassword.done") },
    onSuccess: (updated) => {
      setStaff(updated);
      navigate("/", { replace: true });
    },
  });

  const serverError = change.error ? (change.error instanceof ApiError ? change.error.message : t("states.errorBody")) : null;

  return (
    <div className="flex min-h-[calc(100dvh-2.5rem)] items-center justify-center px-4 py-8">
      <div className="w-full max-w-md animate-rise rounded-2xl border border-line bg-surface p-6 shadow-pop md:p-8">
        <div className="flex items-center gap-3">
          <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand text-brand-ink">
            <HeartPulse aria-hidden className="size-5" />
          </span>
          <span className="text-lg font-semibold">{t("app.name")}</span>
        </div>
        <h1 className="mt-6 flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <KeyRound aria-hidden className="size-6 text-brand" />
          {t("setPassword.title")}
        </h1>
        <p className="mt-1 text-muted">{t("setPassword.body", { name: staff?.full_name ?? "" })}</p>

        <form
          className="mt-6 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            const problem = passwordProblem(next, { username: staff?.username ?? "", current, confirm });
            setLocalError(problem ? t(`setPassword.problem.${problem}`) : null);
            if (!problem) change.mutate();
          }}
        >
          <Field label={t("setPassword.current")} htmlFor="current_password">
            <Input id="current_password" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
          </Field>
          <Field label={t("setPassword.new")} htmlFor="new_password" hint={t("setPassword.rule")}>
            <Input id="new_password" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required />
          </Field>
          <Field label={t("setPassword.confirm")} htmlFor="confirm_password">
            <Input id="confirm_password" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
          </Field>
          {(localError || serverError) && <Alert kind="problem">{localError ?? serverError}</Alert>}
          <Button type="submit" className="w-full" disabled={change.isPending}>
            {change.isPending ? t("setPassword.saving") : t("setPassword.submit")}
          </Button>
        </form>
        <button
          type="button"
          onClick={() => void signOut()}
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 text-sm font-semibold text-muted hover:text-ink"
        >
          <LogOut aria-hidden className="size-4" />
          {t("nav.signOut")}
        </button>
      </div>
    </div>
  );
}
