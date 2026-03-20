export function formatTimestamp(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function toYouTubeUrl(videoId, seconds) {
  return `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds)}`;
}

// Quick test (manual):
// console.log(formatTimestamp(12.04)); // expected "12:04"
// console.log(toYouTubeUrl("abc123", 90)); // https://www.youtube.com/watch?v=abc123&t=90

