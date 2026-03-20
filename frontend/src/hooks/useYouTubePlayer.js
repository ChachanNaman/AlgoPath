import { useCallback, useEffect, useRef, useState } from "react";

// Minimal YouTube IFrame API hook.
// Creates a player inside the given `elementId` div and exposes seek/play/pause helpers.
export default function useYouTubePlayer(elementId, videoId) {
  const playerRef = useRef(null);
  const [isReady, setIsReady] = useState(false);

  const createPlayer = useCallback(() => {
    if (!window.YT || !window.YT.Player) return;
    const el = document.getElementById(elementId);
    if (!el) return;

    // Destroy any existing player first (handles hot reload / videoId changes).
    if (playerRef.current && typeof playerRef.current.destroy === "function") {
      try {
        playerRef.current.destroy();
      } catch {
        // ignore
      }
    }

    playerRef.current = new window.YT.Player(elementId, {
      videoId,
      width: "100%",
      height: "100%",
      playerVars: { rel: 0, modestbranding: 1 },
      events: {
        onReady: () => setIsReady(true),
      },
    });
  }, [elementId, videoId]);

  useEffect(() => {
    setIsReady(false);
    if (window.YT && window.YT.Player) {
      createPlayer();
      return () => {
        if (playerRef.current && typeof playerRef.current.destroy === "function") {
          try {
            playerRef.current.destroy();
          } catch {
            // ignore
          }
        }
      };
    }

    // Wait for YouTube IFrame API callback.
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      try {
        if (typeof prev === "function") prev();
      } finally {
        createPlayer();
      }
    };

    return () => {
      window.onYouTubeIframeAPIReady = prev;
      if (playerRef.current && typeof playerRef.current.destroy === "function") {
        try {
          playerRef.current.destroy();
        } catch {
          // ignore
        }
      }
      playerRef.current = null;
    };
  }, [createPlayer]);

  const seekTo = useCallback((seconds) => {
    const p = playerRef.current;
    if (!p || typeof p.seekTo !== "function") return;
    p.seekTo(seconds, true);
  }, []);

  const playVideo = useCallback(() => {
    const p = playerRef.current;
    if (!p || typeof p.playVideo !== "function") return;
    p.playVideo();
  }, []);

  const pauseVideo = useCallback(() => {
    const p = playerRef.current;
    if (!p || typeof p.pauseVideo !== "function") return;
    p.pauseVideo();
  }, []);

  return { playerRef, isReady, seekTo, playVideo, pauseVideo };
}

// Quick manual test:
// - Ensure `frontend/index.html` includes `https://www.youtube.com/iframe_api`
// - Render a div: <div id="yt-player" />
// - Call: useYouTubePlayer("yt-player", "<videoId>")

