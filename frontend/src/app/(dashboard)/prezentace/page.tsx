"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Play,
  Pause,
  Maximize,
  Volume2,
  VolumeX,
  RotateCcw,
  Download,
  Presentation,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PrezentacePage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(0.5);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  }, []);

  const restart = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = 0;
    video.play();
    setIsPlaying(true);
  }, []);

  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const video = videoRef.current;
    if (!video) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    video.currentTime = pos * video.duration;
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      setProgress((video.currentTime / video.duration) * 100);
    };
    const onLoadedMetadata = () => setDuration(video.duration);
    const onEnded = () => setIsPlaying(false);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    video.playbackRate = 0.5;

    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("ended", onEnded);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);

    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("ended", onEnded);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  // 23 slides with transitions (0.5s overlap between each)
  // Timestamps: each slide starts at prev_start + prev_duration - 0.5s
  const slides = [
    // ACT 1: Úvod
    { time: 0, label: "Titulní slide" },
    { time: 4.5, label: "Problém" },
    { time: 9, label: "Řešení" },
    // ACT 2: Příběh zakázky
    { time: 13.5, label: "Email přichází" },
    { time: 21, label: "Zakázka vzniká" },
    { time: 28.5, label: "Kalkulace" },
    { time: 36, label: "Podobné zakázky" },
    { time: 41.5, label: "Nabídka" },
    { time: 47, label: "Kanban pipeline" },
    { time: 54.5, label: "Výrobní operace" },
    { time: 62, label: "Pohoda sync" },
    // ACT 3: Inteligentní funkce
    { time: 69.5, label: "AI Email Agent" },
    { time: 76, label: "Orchestrační pipeline" },
    { time: 83.5, label: "Dashboard" },
    { time: 90, label: "AI Doporučení" },
    { time: 96.5, label: "Reporting" },
    { time: 103, label: "Materiály" },
    { time: 109.5, label: "Dokumenty + OCR" },
    // ACT 4: Tým a výsledky
    { time: 116, label: "Tržiště úkolů" },
    { time: 120.5, label: "Monitoring" },
    { time: 126, label: "Bezpečnost" },
    { time: 130.5, label: "Statistiky" },
    { time: 135, label: "Závěr" },
  ];

  const changeSpeed = useCallback((rate: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = rate;
    setPlaybackRate(rate);
  }, []);

  const jumpToSlide = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    if (video.paused) {
      video.play();
      setIsPlaying(true);
    }
  }, []);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
            <Presentation className="h-7 w-7 text-primary" />
            Prezentace projektu
          </h1>
          <p className="text-muted-foreground mt-1">
            infer<span className="font-bold">box</span> — automatizační platforma pro strojírenství
          </p>
        </div>
        <a
          href="/infer-forge.mp4"
          download="inferbox_prezentace.mp4"
          className="inline-flex"
        >
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Stáhnout MP4
          </Button>
        </a>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-6">
        {/* Video player */}
        <div
          ref={containerRef}
          className="rounded-xl overflow-hidden bg-black border border-border shadow-lg"
        >
          <div className="relative group cursor-pointer" onClick={togglePlay}>
            <video
              ref={videoRef}
              className="w-full aspect-video"
              src="/infer-forge.mp4"
              preload="metadata"
              playsInline
            />

            {/* Play overlay */}
            {!isPlaying && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity">
                <div className="rounded-full bg-primary/90 p-5 shadow-2xl">
                  <Play className="h-10 w-10 text-primary-foreground ml-1" />
                </div>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="bg-card/95 backdrop-blur px-4 py-3 space-y-2">
            {/* Progress bar */}
            <div
              className="h-2 bg-muted rounded-full cursor-pointer group/bar"
              onClick={handleSeek}
            >
              <div
                className="h-full bg-primary rounded-full relative transition-all"
                style={{ width: `${progress}%` }}
              >
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-primary rounded-full shadow-md opacity-0 group-hover/bar:opacity-100 transition-opacity" />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9"
                  onClick={(e) => {
                    e.stopPropagation();
                    togglePlay();
                  }}
                >
                  {isPlaying ? (
                    <Pause className="h-5 w-5" />
                  ) : (
                    <Play className="h-5 w-5" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9"
                  onClick={(e) => {
                    e.stopPropagation();
                    restart();
                  }}
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleMute();
                  }}
                >
                  {isMuted ? (
                    <VolumeX className="h-5 w-5" />
                  ) : (
                    <Volume2 className="h-5 w-5" />
                  )}
                </Button>
                <div className="flex items-center gap-1 ml-2 border rounded-lg px-1">
                  {[0.5, 0.75, 1, 1.5].map((rate) => (
                    <button
                      key={rate}
                      onClick={(e) => {
                        e.stopPropagation();
                        changeSpeed(rate);
                      }}
                      className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                        playbackRate === rate
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {rate}×
                    </button>
                  ))}
                </div>
                <span className="text-sm text-muted-foreground tabular-nums ml-2">
                  {formatTime(currentTime)} / {formatTime(duration)}
                </span>
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFullscreen();
                }}
              >
                <Maximize className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Chapter navigation */}
        <div className="rounded-xl border bg-card p-4">
          <h3 className="font-semibold mb-3 text-sm uppercase tracking-wider text-muted-foreground">
            Kapitoly
          </h3>
          <div className="space-y-1">
            {slides.map((slide, i) => {
              const isActive =
                currentTime >= slide.time &&
                (i === slides.length - 1 || currentTime < slides[i + 1].time);

              return (
                <button
                  key={slide.time}
                  onClick={() => jumpToSlide(slide.time)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-3 ${
                    isActive
                      ? "bg-primary text-primary-foreground font-medium"
                      : "hover:bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="tabular-nums text-xs opacity-70 w-8">
                    {formatTime(slide.time)}
                  </span>
                  <span>{slide.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">Délka</div>
          <div className="text-2xl font-bold mt-1">~140 sekund</div>
          <div className="text-xs text-muted-foreground mt-1">
            23 kapitol, 4 akty
          </div>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">Rozlišení</div>
          <div className="text-2xl font-bold mt-1">1920 × 1080</div>
          <div className="text-xs text-muted-foreground mt-1">
            Full HD, 30 fps
          </div>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">Technologie</div>
          <div className="text-2xl font-bold mt-1">Remotion</div>
          <div className="text-xs text-muted-foreground mt-1">
            React-based video, programatické animace
          </div>
        </div>
      </div>
    </div>
  );
}
