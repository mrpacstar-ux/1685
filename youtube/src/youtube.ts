import fs from "node:fs";
import path from "node:path";
import { google } from "googleapis";
import { CONFIG } from "./config.js";
import { renderDescription } from "./metadata.js";
import type { Metadata } from "./schemas.js";
import { readJson, log } from "./utils.js";

export interface UploadResult {
  status: "uploaded" | "dry-run";
  videoId?: string;
  reason?: string;
}

export interface UploadOptions {
  /** Override the default privacy for this upload. */
  privacy?: "private" | "unlisted" | "public";
  /** RFC3339 timestamp to auto-publish at. Forces privacy to `private` (a
   *  YouTube requirement for scheduled videos) until that time. */
  publishAt?: string;
}

function hasCredentials(): boolean {
  const { clientId, clientSecret, refreshToken } = CONFIG.youtube;
  return Boolean(clientId && clientSecret && refreshToken);
}

function oauthClient() {
  const { clientId, clientSecret, refreshToken } = CONFIG.youtube;
  const client = new google.auth.OAuth2(clientId, clientSecret);
  client.setCredentials({ refresh_token: refreshToken });
  return client;
}

/**
 * Upload a produced package directory (containing metadata.json and video.mp4)
 * to YouTube. Without OAuth credentials, performs a dry run that reports
 * exactly what would be uploaded. New videos default to `private` so a human
 * approves before going public.
 */
export async function uploadPackage(
  dir: string,
  opts: UploadOptions = {},
): Promise<UploadResult> {
  const meta = readJson<Metadata>(path.join(dir, "metadata.json"));
  const videoFile = path.join(dir, "video.mp4");
  const thumbFile = path.join(dir, "thumbnail.png");
  const description = renderDescription(meta);

  // Scheduled uploads must be private until publishAt; otherwise use the
  // requested/default privacy.
  const privacy = opts.publishAt ? "private" : opts.privacy ?? CONFIG.youtube.privacy;
  const when = opts.publishAt ? ` → auto-publish at ${opts.publishAt}` : "";

  if (!hasCredentials()) {
    log("info", "YouTube credentials not set — dry run.");
    log("info", `  title:   ${meta.chosen_title}`);
    log("info", `  privacy: ${privacy}${when}`);
    log("info", `  video:   ${fs.existsSync(videoFile) ? "video.mp4" : "(not rendered)"}`);
    return { status: "dry-run", reason: "no credentials" };
  }
  if (!fs.existsSync(videoFile)) {
    return { status: "dry-run", reason: "video.mp4 not found — render it first" };
  }

  const youtube = google.youtube({ version: "v3", auth: oauthClient() });
  log("run", `Uploading "${meta.chosen_title}" (${privacy})${when}…`);

  const res = await youtube.videos.insert({
    part: ["snippet", "status"],
    requestBody: {
      snippet: {
        title: meta.chosen_title.slice(0, 100),
        description,
        tags: meta.tags,
        categoryId: "28", // Science & Technology
      },
      status: {
        privacyStatus: privacy,
        publishAt: opts.publishAt,
        selfDeclaredMadeForKids: false,
      },
    },
    media: { body: fs.createReadStream(videoFile) },
  });

  const videoId = res.data.id ?? undefined;
  if (videoId && fs.existsSync(thumbFile)) {
    try {
      await youtube.thumbnails.set({
        videoId,
        media: { body: fs.createReadStream(thumbFile) },
      });
    } catch (err) {
      log("warn", `Thumbnail upload failed: ${(err as Error).message}`);
    }
  }

  log("ok", `Uploaded: https://youtu.be/${videoId}`);
  return { status: "uploaded", videoId };
}
