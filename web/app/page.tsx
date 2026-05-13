import type { Metadata } from "next";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  Rss,
  Timer,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getDashboardData } from "@/lib/signal-api";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "Monitor feed health, top curated articles by score, and recent ingestion jobs for the Signal curation pipeline.",
  keywords: [
    "Signal",
    "RSS",
    "feed quality",
    "backend",
    "curation",
    "dashboard",
  ],
  openGraph: {
    title: "Signal · Dashboard",
    description:
      "Feed quality metrics, curated highlights, and job run history in one view.",
    type: "website",
  },
};

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatDate(value: string | null) {
  if (!value) {
    return "Never";
  }
  return dateTimeFormatter.format(new Date(value));
}

function getFeedStatusClasses(status: "healthy" | "degraded" | "disabled") {
  switch (status) {
    case "healthy":
      return "bg-[#e0f6ff] text-[#1b2540]";
    case "degraded":
      return "bg-[#fff4e8] text-[#1b2540]";
    default:
      return "bg-white text-[#7c8293]";
  }
}

function getJobStatusClasses(status: "success" | "error" | "skipped_locked") {
  switch (status) {
    case "success":
      return "bg-[#e0f6ff] text-[#1b2540]";
    case "error":
      return "bg-[#fff1f1] text-[#1b2540]";
    default:
      return "bg-white text-[#7c8293]";
  }
}

function getExportStatusClasses(status: "pending" | "exported" | "failed" | "none") {
  switch (status) {
    case "exported":
      return "bg-[#e0f6ff] text-[#1b2540]";
    case "failed":
      return "bg-[#fff1f1] text-[#1b2540]";
    case "pending":
      return "bg-[#fff4e8] text-[#1b2540]";
    default:
      return "bg-white text-[#7c8293]";
  }
}

function compareFeeds(
  a: { name: string; curated_rate: number; scored_articles: number },
  b: { name: string; curated_rate: number; scored_articles: number },
) {
  const curatedGap = Math.abs(a.curated_rate - b.curated_rate);
  // If curated rates are close (<=10pp), favor stronger evidence volume.
  if (curatedGap <= 0.1 && b.scored_articles !== a.scored_articles) {
    return b.scored_articles - a.scored_articles;
  }
  if (b.curated_rate !== a.curated_rate) {
    return b.curated_rate - a.curated_rate;
  }
  if (b.scored_articles !== a.scored_articles) {
    return b.scored_articles - a.scored_articles;
  }
  return a.name.localeCompare(b.name);
}

type FeedRowProps = {
  feed: {
    id: number;
    name: string;
    category: string;
    quality_status: "healthy" | "degraded" | "disabled";
    curated_rate: number;
    scored_articles: number;
    consecutive_failures: number;
  };
};

function FeedRow({ feed }: FeedRowProps) {
  return (
    <div className="rounded-2xl border border-[#2a3f70] bg-[#1a2f5e] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{feed.name}</p>
          <p className="mt-1 text-xs text-[#b7c6ec]">Category: {feed.category}</p>
        </div>
        <Badge className={`capitalize shadow-none ${getFeedStatusClasses(feed.quality_status)}`}>
          {feed.quality_status}
        </Badge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-[#c7d3f1]">
        <p>Curated {Math.round(feed.curated_rate * 100)}%</p>
        <p>{feed.scored_articles} scored</p>
        <p>Failures {feed.consecutive_failures}</p>
      </div>
    </div>
  );
}

type ArticleRowProps = {
  article: {
    id: number;
    title: string;
    feed_name: string;
    score: number;
    created_at: string;
    tags: string[];
    obsidian_export_status: "pending" | "exported" | "failed" | "none";
  };
};

function ArticleRow({ article }: ArticleRowProps) {
  return (
    <div className="rounded-2xl border border-[#2a3f70] bg-[#1a2f5e] p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        <p className="line-clamp-2 text-sm font-semibold text-white">{article.title}</p>
        <Badge
          className={`shrink-0 text-[11px] capitalize shadow-none ${getExportStatusClasses(article.obsidian_export_status)}`}
        >
          Obsidian: {article.obsidian_export_status}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-[#c7d3f1]">
        {article.feed_name} - Score {article.score.toFixed(2)} - {formatDate(article.created_at)}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {article.tags.slice(0, 3).map((tag) => (
          <Badge key={tag} className="bg-[#243d73] text-[11px] text-[#dce6ff] shadow-none">
            #{tag}
          </Badge>
        ))}
      </div>
    </div>
  );
}

export default async function Home() {
  const result = await getDashboardData()
    .then((data) => ({ data, error: null as string | null }))
    .catch((error: unknown) => ({
      data: null,
      error: error instanceof Error ? error.message : "Unknown error",
    }));

  if (!result.data) {
    return (
      <main className="flex flex-1 items-center justify-center bg-[#f8f9fc] p-6">
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Unable to load dashboard data</CardTitle>
            <CardDescription>
              Check `SIGNAL_API_BASE_URL` and `SIGNAL_API_KEY` in `web/.env.local`, then retry.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-[#6b7184]">{result.error}</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  const { feeds, articles, jobs } = result.data;
  const healthyFeeds = feeds.filter((feed) => feed.quality_status === "healthy").length;
  const curatedRate =
    feeds.length > 0
      ? Math.round((feeds.reduce((acc, feed) => acc + feed.curated_rate, 0) / feeds.length) * 100)
      : 0;
  const sortedFeeds = [...feeds].sort(compareFeeds);
  const visibleFeeds = sortedFeeds.slice(0, 5);
  const visibleArticles = articles.items.slice(0, 5);
  const hasMoreFeeds = sortedFeeds.length > 5;
  const hasMoreArticles = articles.items.length > 5;

  return (
    <div className="flex flex-1 flex-col bg-[#0b1736] text-[#dce6ff]">
      <header className="bg-[linear-gradient(180deg,#4ea9ea_0%,#1f5fcb_38%,#10357a_68%,#0b1736_100%)] text-white">
        <div className="mx-auto flex min-h-[58vh] max-w-6xl flex-col items-start justify-center px-6 py-20 sm:py-24">
          <Badge className="mb-6 self-start bg-white/10 text-white shadow-[rgba(255,255,255,0.15)_0px_0px_0px_1px_inset]">
            Signal / Backend Career Operating System
          </Badge>
          <h1 className="max-w-4xl text-balance text-5xl font-semibold tracking-[-0.02em] sm:text-6xl">
            Discover, evaluate, and ship high-quality backend insights.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-white/85">
            Track what matters: source quality, high-signal curation, and scheduler health in one
            focused command center.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild className="h-12 px-6 text-base">
              <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
                Open API Docs
              </a>
            </Button>
            <Button asChild variant="secondary" className="h-12 px-6 text-base">
              <a href="https://github.com/jeremyjsx" target="_blank" rel="noreferrer">
                View GitHub Profile
              </a>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-10 text-[#dce6ff]">
        <section className="rounded-[24px] p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
              <CardHeader>
                <CardDescription className="flex items-center gap-2 text-[#b7c6ec]">
                  <Rss aria-hidden="true" focusable="false" className="h-4 w-4" /> Feeds Monitored
                </CardDescription>
                <CardTitle className="text-3xl text-white">{feeds.length}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-[#c7d3f1]">Sources actively tracked by the pipeline.</p>
              </CardContent>
            </Card>
            <Card className="bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
              <CardHeader>
                <CardDescription className="flex items-center gap-2 text-[#b7c6ec]">
                  <CheckCircle2 aria-hidden="true" focusable="false" className="h-4 w-4" /> Healthy Feeds
                </CardDescription>
                <CardTitle className="text-3xl text-white">{healthyFeeds}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-[#c7d3f1]">
                  {feeds.length ? Math.round((healthyFeeds / feeds.length) * 100) : 0}% currently healthy.
                </p>
              </CardContent>
            </Card>
            <Card className="bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
              <CardHeader>
                <CardDescription className="flex items-center gap-2 text-[#b7c6ec]">
                  <FileText aria-hidden="true" focusable="false" className="h-4 w-4" /> Curated Insights
                </CardDescription>
                <CardTitle className="text-3xl text-white">{articles.total}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-[#c7d3f1]">First 5 shown below, with load more available.</p>
              </CardContent>
            </Card>
            <Card className="bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
              <CardHeader>
                <CardDescription className="flex items-center gap-2 text-[#b7c6ec]">
                  <Clock3 aria-hidden="true" focusable="false" className="h-4 w-4" /> Curated Rate
                </CardDescription>
                <CardTitle className="text-3xl text-white">{curatedRate}%</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-2 rounded-full bg-[#2b3e6e]">
                  <div className="h-2 rounded-full bg-[#5fbdf7]" style={{ width: `${curatedRate}%` }} />
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="grid gap-6 rounded-[24px] p-5 lg:grid-cols-2 lg:items-stretch sm:p-6">
          <Card className="relative h-[700px] overflow-hidden bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
            <Badge className="absolute right-6 top-6 bg-[#243d73] text-[#dce6ff]">
              {feeds.length} sources
            </Badge>
            <CardHeader className="pr-28">
              <div>
                <CardTitle className="text-white">Feed Quality</CardTitle>
                <CardDescription className="text-[#b7c6ec]">
                  Top 5 ranked by curated rate, with scored coverage as a smart tiebreak.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="relative space-y-4 overflow-hidden pb-14">
              {feeds.length === 0 ? (
                <div className="rounded-2xl bg-[#1a2f5e] p-4 text-sm text-[#c7d3f1]">
                  No feed data yet. Source quality appears after the first ingestion run.
                </div>
              ) : (
                <>
                  {visibleFeeds.map((feed) => (
                    <FeedRow key={feed.id} feed={feed} />
                  ))}
                </>
              )}
            </CardContent>
            {hasMoreFeeds ? (
              <>
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 rounded-b-[20px] bg-gradient-to-b from-transparent via-[#162a52]/90 to-[#162a52]" />
                <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-[#243d73] px-3 py-1 text-xs text-[#dce6ff]">
                  More feeds available
                </p>
              </>
            ) : null}
          </Card>

          <Card className="relative h-[700px] overflow-hidden bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
            <Badge className="absolute right-6 top-6 bg-[#243d73] text-[#dce6ff]">
              Latest scored
            </Badge>
            <CardHeader className="pr-28">
              <div>
                <CardTitle className="text-white">Curated Articles Queue</CardTitle>
                <CardDescription className="text-[#b7c6ec]">
                  Top 5 high-signal picks ready for notes, summaries, or Obsidian export.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="relative space-y-4 overflow-hidden pb-14">
              {articles.items.length === 0 ? (
                <div className="rounded-2xl bg-[#1a2f5e] p-4 text-sm text-[#c7d3f1]">
                  No curated items yet. This queue fills after scoring and keep/discard decisions.
                </div>
              ) : (
                <>
                  {visibleArticles.map((article) => (
                    <ArticleRow key={article.id} article={article} />
                  ))}
                </>
              )}
            </CardContent>
            {hasMoreArticles ? (
              <>
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 rounded-b-[20px] bg-gradient-to-b from-transparent via-[#162a52]/90 to-[#162a52]" />
                <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-[#243d73] px-3 py-1 text-xs text-[#dce6ff]">
                  More articles available
                </p>
              </>
            ) : null}
          </Card>
        </section>

        <section className="rounded-[24px] p-5 sm:p-6">
          <Card className="relative bg-[#162a52] backdrop-blur-sm shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]">
            <Badge className="absolute right-6 top-6 bg-[#243d73] text-[#dce6ff]">
              <Timer aria-hidden="true" focusable="false" className="mr-1 h-3.5 w-3.5" /> Scheduler Health
            </Badge>
            <CardHeader className="pr-36">
              <div>
                <CardTitle className="text-white">Scheduler Job Runs</CardTitle>
                <CardDescription className="text-[#b7c6ec]">Recent executions for feed fetch and cleanup jobs.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {jobs.length === 0 ? (
                <div className="rounded-2xl bg-[#1a2f5e] p-4 text-sm text-[#c7d3f1]">
                  No job history available yet. Recent outcomes appear after scheduler runs.
                </div>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#1a2f5e] p-4 shadow-[rgba(0,0,0,0.22)_0px_0px_0px_1px]"
                  >
                    <div>
                      <p className="text-sm font-semibold text-white">{job.job_name}</p>
                      <p className="text-xs text-[#c7d3f1]">
                        Started {formatDate(job.started_at)} - Finished {formatDate(job.finished_at)}
                      </p>
                    </div>
                    <Badge className={`capitalize shadow-none ${getJobStatusClasses(job.status)}`}>
                      {job.status === "error" ? (
                        <AlertTriangle aria-hidden="true" focusable="false" className="mr-1 h-3.5 w-3.5" />
                      ) : (
                        <Activity aria-hidden="true" focusable="false" className="mr-1 h-3.5 w-3.5" />
                      )}
                      {job.status.replace("_", " ")}
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
