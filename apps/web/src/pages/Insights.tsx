import { useQuery } from "@tanstack/react-query";
import { BarChart3, CalendarCheck, ClipboardCheck, FileClock, Send, TrendingUp, Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { trendsApi } from "../api/client";
import { AreaChart, BarList, StackedColumns } from "../components/charts";
import { PageHeader } from "../components/PageHeader";
import { errorStateKind, PageState } from "../components/PageState";
import { Card, CardHeader } from "../components/ui/card";
import { CardSkeleton, Skeleton, StatTile } from "../components/ui/kit";

const REFERRAL_STEPS = ["SENT", "CONTACTED", "ATTENDED", "ADVICE_RECEIVED", "FOLLOW_UP_COMPLETED", "CLOSED"];

/** "2026-11-02" -> "2 Nov" in the UI language, without a time-zone shift. */
function weekLabel(iso: string, lang: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(lang, { day: "numeric", month: "short" });
}

function EmptyChart({ text }: { text: string }) {
  return (
    <div className="flex h-[220px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line bg-page/60 px-6 text-center">
      <BarChart3 aria-hidden className="size-6 text-faint" />
      <p className="text-sm text-muted">{text}</p>
    </div>
  );
}

/** Programme figures from /overview/trends: administrative counts only. */
export function Insights() {
  const { t, i18n } = useTranslation();
  const trends = useQuery({ queryKey: ["trends"], queryFn: trendsApi.get });

  if (trends.isError) return <PageState kind={errorStateKind(trends.error)} />;

  const data = trends.data;
  const labels = data?.week_starts.map((w) => weekLabel(w, i18n.language)) ?? [];
  const tiles = data?.tiles;
  const value = (n: number | undefined) => (n === undefined ? <Skeleton className="h-8 w-12" /> : n);
  const onTime =
    tiles === undefined ? (
      <Skeleton className="h-8 w-16" />
    ) : tiles.follow_ups_closed === 0 ? (
      "—"
    ) : (
      `${Math.round((tiles.follow_ups_closed_on_time / tiles.follow_ups_closed) * 100)}%`
    );

  return (
    <div className="space-y-6">
      <PageHeader title={t("insights.title")} description={t("insights.description")} />

      <section aria-label={t("insights.tilesLabel")} className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
        <StatTile label={t("insights.active")} value={value(tiles?.active_pregnancies)} icon={Users} hint={t("insights.activeHint")} />
        <StatTile label={t("insights.visits")} value={value(tiles?.visits_this_month)} icon={CalendarCheck} hint={t("insights.visitsHint")} />
        <StatTile
          label={t("insights.closedOnTime")}
          value={onTime}
          icon={ClipboardCheck}
          hint={
            tiles && tiles.follow_ups_closed > 0
              ? t("insights.closedOnTimeHint", { onTime: tiles.follow_ups_closed_on_time, closed: tiles.follow_ups_closed })
              : t("insights.closedOnTimeNone")
          }
        />
        <StatTile
          label={t("insights.reports")}
          value={value(tiles?.reports_awaiting_review)}
          icon={FileClock}
          tone="accent"
          hint={t("insights.reportsHint")}
        />
      </section>

      {!data ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <CardSkeleton lines={6} />
          <CardSkeleton lines={6} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
            <Card>
              <CardHeader icon={TrendingUp} title={t("insights.registrations")} description={t("insights.registrationsBody")} />
              {data.registrations.some(Boolean) ? (
                <AreaChart data={data.registrations.map((v, i) => ({ label: labels[i], value: v }))} caption={t("insights.registrations")} />
              ) : (
                <EmptyChart text={t("insights.registrationsEmpty")} />
              )}
            </Card>
            <Card>
              <CardHeader icon={CalendarCheck} title={t("insights.visitsChart")} description={t("insights.visitsChartBody")} />
              {data.visits_attended.some(Boolean) || data.visits_missed.some(Boolean) ? (
                <StackedColumns
                  rows={data.visits_attended.map((v, i) => ({ label: labels[i], values: [v, data.visits_missed[i]] }))}
                  series={[t("insights.attended"), t("insights.missed")]}
                  caption={t("insights.visitsChart")}
                />
              ) : (
                <EmptyChart text={t("insights.visitsEmpty")} />
              )}
            </Card>
          </div>
          <Card>
            <CardHeader icon={Send} title={t("insights.referrals")} description={t("insights.referralsBody")} />
            <BarList
              className="max-w-2xl"
              caption={t("insights.referrals")}
              data={REFERRAL_STEPS.map((s) => ({ label: t(`records.ref.status${s}`), value: data.referrals_by_status[s] ?? 0 }))}
            />
          </Card>
          <p className="text-sm text-muted">{t("insights.footnote")}</p>
        </>
      )}
    </div>
  );
}
