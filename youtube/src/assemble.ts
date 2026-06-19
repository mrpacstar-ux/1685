import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { ensureDir, commandExists, log } from "./utils.js";

export interface AssembleResult {
  status: "rendered" | "skipped";
  file?: string;
  reason?: string;
}

function run(cmd: string, args: string[]): { ok: boolean; stderr: string } {
  const res = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 1 << 26 });
  return { ok: res.status === 0, stderr: res.stderr ?? "" };
}

function audioDuration(audioFile: string): number {
  const res = spawnSync(
    "ffprobe",
    [
      "-v", "error",
      "-show_entries", "format=duration",
      "-of", "default=nw=1:nk=1",
      audioFile,
    ],
    { encoding: "utf8" },
  );
  const seconds = parseFloat((res.stdout ?? "").trim());
  return Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
}

const VF =
  "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30";

/**
 * Assemble a narrated montage: each B-roll clip is normalized to 1080p/30fps
 * and timed so the concatenation matches the narration length, then the
 * voiceover is laid over the top. Skips cleanly if ffmpeg, clips, or audio
 * are unavailable.
 */
export function assembleVideo(
  clips: string[],
  audioFile: string | undefined,
  dir: string,
): AssembleResult {
  if (!commandExists("ffmpeg") || !commandExists("ffprobe")) {
    return skip("ffmpeg/ffprobe not found on PATH");
  }
  if (!audioFile || !fs.existsSync(audioFile)) {
    return skip("no voiceover audio (set a TTS provider to enable rendering)");
  }
  if (clips.length === 0) {
    return skip("no B-roll clips (set PEXELS_API_KEY to enable rendering)");
  }

  const duration = audioDuration(audioFile);
  if (!duration) return skip("could not read narration duration");

  const tmp = ensureDir(path.join(dir, ".render"));
  const perClip = Math.max(2, duration / clips.length);
  const segments: string[] = [];

  for (let i = 0; i < clips.length; i++) {
    const seg = path.join(tmp, `seg-${String(i).padStart(3, "0")}.mp4`);
    const { ok, stderr } = run("ffmpeg", [
      "-y",
      "-stream_loop", "-1", // loop a short clip to fill its slot
      "-i", clips[i],
      "-t", perClip.toFixed(2),
      "-vf", VF,
      "-an",
      "-c:v", "libx264",
      "-preset", "veryfast",
      "-pix_fmt", "yuv420p",
      "-r", "30",
      seg,
    ]);
    if (!ok) {
      log("warn", `Clip ${i} failed to normalize; skipping it.`);
      if (process.env.PBM_DEBUG) console.error(stderr);
      continue;
    }
    segments.push(seg);
  }

  if (segments.length === 0) return skip("all clips failed to normalize");

  const listFile = path.join(tmp, "concat.txt");
  fs.writeFileSync(
    listFile,
    segments.map((s) => `file '${s.replace(/'/g, "'\\''")}'`).join("\n") + "\n",
  );

  const silentVideo = path.join(tmp, "video-silent.mp4");
  const concat = run("ffmpeg", [
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", listFile,
    "-c", "copy",
    silentVideo,
  ]);
  if (!concat.ok) {
    if (process.env.PBM_DEBUG) console.error(concat.stderr);
    return skip("ffmpeg concat failed (run with PBM_DEBUG=1 for details)");
  }

  const out = path.join(dir, "video.mp4");
  const mux = run("ffmpeg", [
    "-y",
    "-i", silentVideo,
    "-i", audioFile,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    out,
  ]);
  if (!mux.ok) {
    if (process.env.PBM_DEBUG) console.error(mux.stderr);
    return skip("ffmpeg mux failed (run with PBM_DEBUG=1 for details)");
  }

  fs.rmSync(tmp, { recursive: true, force: true });
  log("ok", `Video rendered: video.mp4 (~${Math.round(duration)}s)`);
  return { status: "rendered", file: out };
}

function skip(reason: string): AssembleResult {
  log("info", `Video assembly skipped (${reason}).`);
  return { status: "skipped", reason };
}
