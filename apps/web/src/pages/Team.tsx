import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, ShieldCheck, UserPlus, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, teamApi, type StaffRoleName, type Team as TeamData, type TeamMember } from "../api/client";
import { Avatar } from "../components/Avatar";
import { PageHeader } from "../components/PageHeader";
import { errorStateKind, PageState } from "../components/PageState";
import { Button } from "../components/ui/button";
import { Card, CardHeader } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/field";
import { Badge, CardSkeleton } from "../components/ui/kit";
import { Alert, StatusBadge } from "../components/ui/status";
import { suggestUsername } from "../lib/team";
import { useSession } from "../state/session";

const ROLES: StaffRoleName[] = ["ASHA", "NURSE", "COORDINATOR", "DOCTOR"];

interface Credentials {
  name: string;
  username: string;
  password: string;
  reset: boolean;
}

/** One-time display of a temporary password, to hand over in person. */
function CredentialsCard({ creds, onDone }: { creds: Credentials; onDone: () => void }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${creds.username}\n${creds.password}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Card className="animate-rise border-brand-soft bg-brand-tint/60">
      <CardHeader
        icon={KeyRound}
        title={creds.reset ? t("team.creds.resetTitle", { name: creds.name }) : t("team.creds.title", { name: creds.name })}
        description={t("team.creds.body")}
      />
      <dl className="grid gap-3 rounded-xl border border-line bg-surface p-4 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold tracking-wide text-faint uppercase">{t("team.creds.username")}</dt>
          <dd className="mt-1 font-mono text-lg text-ink">{creds.username}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold tracking-wide text-faint uppercase">{t("team.creds.password")}</dt>
          <dd className="mt-1 font-mono text-lg tracking-wide text-ink">{creds.password}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Button variant="secondary" onClick={copy}>
          {copied ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />}
          {copied ? t("team.creds.copied") : t("team.creds.copy")}
        </Button>
        <Button onClick={onDone}>{t("team.creds.done")}</Button>
      </div>
    </Card>
  );
}

function AddStaffForm({ team, onCreated, onCancel }: { team: TeamData; onCreated: (c: Credentials) => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const facilities = team.facilities.filter((f) => f.active);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [touchedUsername, setTouchedUsername] = useState(false);
  const [facilityId, setFacilityId] = useState(facilities[0]?.id ?? "");
  const [role, setRole] = useState<StaffRoleName>("ASHA");

  const create = useMutation({
    mutationFn: () =>
      teamApi.create({ organization_id: team.organization_id, username, full_name: fullName, facility_id: facilityId, role }),
    meta: { silent: true },
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["team", team.organization_id] });
      onCreated({ name: created.full_name, username: created.username, password: created.temporary_password ?? "", reset: false });
    },
  });

  return (
    <Card className="animate-rise">
      <CardHeader icon={UserPlus} title={t("team.add.title")} description={t("team.add.body")} />
      <form
        className="grid gap-4 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Field label={t("team.add.fullName")} htmlFor="team_full_name">
          <Input
            id="team_full_name"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              if (!touchedUsername) setUsername(suggestUsername(e.target.value));
            }}
            required
            autoComplete="off"
          />
        </Field>
        <Field label={t("team.add.username")} htmlFor="team_username" hint={t("team.add.usernameHint")}>
          <Input
            id="team_username"
            value={username}
            onChange={(e) => {
              setTouchedUsername(true);
              setUsername(e.target.value.toLowerCase());
            }}
            required
            autoComplete="off"
            className="font-mono"
          />
        </Field>
        <Field label={t("team.add.facility")} htmlFor="team_facility">
          <Select id="team_facility" value={facilityId} onChange={(e) => setFacilityId(e.target.value)} required>
            {facilities.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("team.add.role")} htmlFor="team_role">
          <Select id="team_role" value={role} onChange={(e) => setRole(e.target.value as StaffRoleName)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`nav.role.${r}`)}
              </option>
            ))}
          </Select>
        </Field>
        {create.isError && (
          <div className="md:col-span-2">
            <Alert kind="problem">{create.error instanceof ApiError ? create.error.message : t("states.errorBody")}</Alert>
          </div>
        )}
        <div className="flex flex-col gap-2 sm:flex-row md:col-span-2">
          <Button type="submit" disabled={create.isPending || !facilityId}>
            <UserPlus aria-hidden className="size-4" />
            {create.isPending ? t("team.add.creating") : t("team.add.submit")}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel}>
            {t("care.cancel")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function MemberRow({ member, orgId, isSelf, onReset }: { member: TeamMember; orgId: string; isSelf: boolean; onReset: (c: Credentials) => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const reload = () => void queryClient.invalidateQueries({ queryKey: ["team", orgId] });

  const reset = useMutation({
    mutationFn: () => teamApi.resetPassword(member.id),
    meta: { silent: true },
    onSuccess: (r) => {
      reload();
      onReset({ name: member.full_name, username: member.username, password: r.temporary_password, reset: true });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : t("states.errorBody")),
  });
  const remove = useMutation({
    mutationFn: (m: { facility_id: string; id: string }) => teamApi.removeRole(m.facility_id, m.id),
    meta: { toast: t("team.removed") },
    onSuccess: reload,
    onError: (e) => setError(e instanceof ApiError ? e.message : t("states.errorBody")),
  });

  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 md:flex-row md:items-center">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <Avatar name={member.full_name} size="sm" />
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 font-semibold text-ink">
            {member.full_name}
            {member.is_org_admin && (
              <Badge tone="brand" icon={ShieldCheck}>
                {t("team.admin")}
              </Badge>
            )}
            {isSelf && <span className="text-sm font-normal text-muted">{t("team.you")}</span>}
          </p>
          <p className="font-mono text-sm text-muted">{member.username}</p>
        </div>
      </div>
      <ul className="flex flex-wrap gap-1.5 md:w-72">
        {member.memberships.map((m) => (
          <li key={m.id} className="inline-flex items-center gap-1 rounded-full border border-line bg-surface py-0.5 pr-1 pl-2.5 text-sm text-ink-2">
            {t(`nav.role.${m.role}`)} · {m.facility_name}
            {!isSelf && (
              <button
                type="button"
                aria-label={t("team.removeRole", { role: t(`nav.role.${m.role}`), facility: m.facility_name, name: member.full_name })}
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(t("team.removeConfirm", { name: member.full_name, facility: m.facility_name }))) remove.mutate(m);
                }}
                className="inline-flex size-6 items-center justify-center rounded-full text-faint hover:bg-subtle hover:text-ink"
              >
                <X aria-hidden className="size-3.5" />
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-2 md:w-64 md:justify-end">
        {member.must_change_password ? (
          <StatusBadge kind="pending">{t("team.status.waiting")}</StatusBadge>
        ) : (
          <StatusBadge kind="confirmed">{t("team.status.active")}</StatusBadge>
        )}
        {!isSelf && (
          <Button
            size="sm"
            variant="ghost"
            disabled={reset.isPending}
            onClick={() => {
              if (window.confirm(t("team.resetConfirm", { name: member.full_name }))) reset.mutate();
            }}
          >
            <KeyRound aria-hidden className="size-3.5" />
            {t("team.reset")}
          </Button>
        )}
      </div>
      {error && (
        <div className="md:basis-full">
          <Alert kind="problem">{error}</Alert>
        </div>
      )}
    </li>
  );
}

/** Organization admins: create staff accounts, reset passwords, remove roles. */
export function Team() {
  const { t } = useTranslation();
  const { staff } = useSession();
  const orgId = staff?.admin_organization_ids[0];
  const team = useQuery({ queryKey: ["team", orgId], queryFn: () => teamApi.get(orgId as string), enabled: !!orgId });
  const [adding, setAdding] = useState(false);
  const [creds, setCreds] = useState<Credentials | null>(null);

  if (!orgId) return <PageState kind="no-access" />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("team.title")}
        description={t("team.description")}
        actions={
          !adding &&
          !creds && (
            <Button onClick={() => setAdding(true)} disabled={!team.data}>
              <UserPlus aria-hidden className="size-4" />
              {t("team.add.open")}
            </Button>
          )
        }
      />

      {creds && <CredentialsCard creds={creds} onDone={() => setCreds(null)} />}
      {adding && team.data && !creds && (
        <AddStaffForm
          team={team.data}
          onCancel={() => setAdding(false)}
          onCreated={(c) => {
            setAdding(false);
            setCreds(c);
          }}
        />
      )}

      {team.isPending && <CardSkeleton lines={5} />}
      {team.isError && <PageState kind={errorStateKind(team.error)} />}
      {team.data && (
        <Card>
          <CardHeader
            icon={ShieldCheck}
            title={t("team.listTitle", { count: team.data.staff.length })}
            description={t("team.listBody")}
          />
          {team.data.staff.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">{t("team.empty")}</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {team.data.staff.map((m) => (
                <MemberRow
                  key={m.id}
                  member={m}
                  orgId={orgId}
                  isSelf={m.id === staff?.id}
                  onReset={(c) => {
                    setAdding(false);
                    setCreds(c);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                />
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}
