import { z } from "zod";

export type FeedQualityItem = {
  id: number;
  name: string;
  category: string;
  active: boolean;
  quality_status: "healthy" | "degraded" | "disabled";
  scored_articles: number;
  curated_articles: number;
  curated_rate: number;
  consecutive_failures: number;
  last_success_at: string | null;
};

export type ArticleItem = {
  id: number;
  title: string;
  feed_name: string;
  score: number;
  created_at: string;
  tags: string[];
  obsidian_export_status: "pending" | "exported" | "failed" | "none";
};

export type ListArticlesResponse = {
  items: ArticleItem[];
  total: number;
  limit: number;
  offset: number;
};

export type JobRunItem = {
  id: number;
  job_name: string;
  status: "success" | "error" | "skipped_locked";
  started_at: string;
  finished_at: string | null;
};

const feedHealthSchema = z.enum(["healthy", "degraded", "disabled"]);
const obsidianExportSchema = z.enum(["pending", "exported", "failed", "none"]);
const jobStatusSchema = z.enum(["success", "error", "skipped_locked"]);

const feedQualityApiItemSchema = z.looseObject({
  feed_id: z.coerce.number().optional(),
  id: z.coerce.number().optional(),
  name: z.string().optional(),
  category: z.string().nullable().optional(),
  is_active: z.boolean().optional(),
  active: z.boolean().optional(),
  health_status: z.string().optional(),
  quality_status: z.string().optional(),
  total_scored: z.coerce.number().optional(),
  scored_articles: z.coerce.number().optional(),
  kept_count: z.coerce.number().optional(),
  curated_articles: z.coerce.number().optional(),
  curated_rate: z.coerce.number().optional(),
  consecutive_failures: z.coerce.number().optional(),
  last_success_at: z.string().nullable().optional(),
});

const feedQualityApiResponseSchema = z.object({
  min_scored_articles: z.coerce.number().optional(),
  min_curated_rate: z.coerce.number().optional(),
  items: z.array(feedQualityApiItemSchema),
});

const feedQualityFetchSchema = z.union([
  feedQualityApiResponseSchema,
  z.array(feedQualityApiItemSchema),
]);

const articleApiItemSchema = z.looseObject({
  id: z.coerce.number(),
  title: z.string().optional(),
  feed_name: z.string().nullable().optional(),
  score: z.coerce.number().nullable().optional(),
  ai_score: z.coerce.number().nullable().optional(),
  fetched_at: z.string().nullable().optional(),
  created_at: z.string().optional(),
  tags: z.preprocess((v) => (Array.isArray(v) ? v : []), z.array(z.string())),
  obsidian_export_status: z.string().nullable().optional(),
});

const listArticlesApiResponseSchema = z.object({
  items: z.array(articleApiItemSchema),
  total: z.coerce.number().optional(),
  limit: z.coerce.number().optional(),
  offset: z.coerce.number().optional(),
});

const jobRunApiItemSchema = z.looseObject({
  id: z.coerce.number(),
  job_name: z.string(),
  status: z.string(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
  new_articles: z.coerce.number().optional(),
  message: z.string().nullable().optional(),
  duration_ms: z.coerce.number().nullable().optional(),
});

const jobRunsFetchSchema = z.union([
  z.array(jobRunApiItemSchema),
  z.object({ items: z.array(jobRunApiItemSchema) }),
  z.object({ value: z.array(jobRunApiItemSchema) }),
]);

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";

function getConfig() {
  return {
    baseUrl: process.env.SIGNAL_API_BASE_URL ?? DEFAULT_API_BASE_URL,
    apiKey: process.env.SIGNAL_API_KEY,
  };
}

async function fetchFromSignal(path: string): Promise<unknown> {
  const { baseUrl, apiKey } = getConfig();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }

  const response = await fetch(`${baseUrl}${path}`, {
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Signal API error ${response.status} on ${path}`);
  }

  return response.json() as Promise<unknown>;
}

function asFeedQualityStatus(value: string | undefined): FeedQualityItem["quality_status"] {
  const parsed = feedHealthSchema.safeParse(value);
  return parsed.success ? parsed.data : "healthy";
}

function asObsidianStatus(
  value: string | null | undefined,
): ArticleItem["obsidian_export_status"] {
  if (value == null || value === "") {
    return "none";
  }
  const parsed = obsidianExportSchema.safeParse(value);
  return parsed.success ? parsed.data : "none";
}

function asJobStatus(value: string | undefined): JobRunItem["status"] {
  const parsed = jobStatusSchema.safeParse(value);
  return parsed.success ? parsed.data : "success";
}

function parseFeedQualityResponse(raw: unknown): FeedQualityItem[] {
  const parsed = feedQualityFetchSchema.parse(raw);
  const items = Array.isArray(parsed) ? parsed : parsed.items;
  return items.map((item) => ({
    id: item.feed_id ?? item.id ?? 0,
    name: item.name ?? "Unknown feed",
    category: item.category ?? "general",
    active: item.is_active ?? item.active ?? true,
    quality_status: asFeedQualityStatus(item.health_status ?? item.quality_status),
    scored_articles: item.total_scored ?? item.scored_articles ?? 0,
    curated_articles: item.kept_count ?? item.curated_articles ?? 0,
    curated_rate: item.curated_rate ?? 0,
    consecutive_failures: item.consecutive_failures ?? 0,
    last_success_at: item.last_success_at ?? null,
  }));
}

function parseListArticlesResponse(raw: unknown): ListArticlesResponse {
  const data = listArticlesApiResponseSchema.parse(raw);
  return {
    items: data.items.map((item) => ({
      id: item.id,
      title: item.title ?? "Untitled",
      feed_name: item.feed_name ?? "Unknown feed",
      score: item.score ?? item.ai_score ?? 0,
      created_at: item.created_at ?? item.fetched_at ?? new Date().toISOString(),
      tags: item.tags,
      obsidian_export_status: asObsidianStatus(item.obsidian_export_status),
    })),
    total: data.total ?? data.items.length,
    limit: data.limit ?? data.items.length,
    offset: data.offset ?? 0,
  };
}

function parseJobRunsResponse(raw: unknown): JobRunItem[] {
  const parsed = jobRunsFetchSchema.parse(raw);
  const rows = Array.isArray(parsed) ? parsed : "items" in parsed ? parsed.items : parsed.value;
  return rows.map((item) => ({
    id: item.id,
    job_name: item.job_name,
    status: asJobStatus(item.status),
    started_at: item.started_at ?? new Date().toISOString(),
    finished_at: typeof item.finished_at === "string" ? item.finished_at : null,
  }));
}

export async function getDashboardData() {
  const [feedsRaw, articlesRaw, jobsRaw] = await Promise.all([
    fetchFromSignal("/feeds/quality?limit=5"),
    fetchFromSignal("/articles?curated=true&limit=8&order_by=score&order_dir=desc"),
    fetchFromSignal("/jobs/runs?limit=5"),
  ]);

  return {
    feeds: parseFeedQualityResponse(feedsRaw),
    articles: parseListArticlesResponse(articlesRaw),
    jobs: parseJobRunsResponse(jobsRaw),
  };
}
