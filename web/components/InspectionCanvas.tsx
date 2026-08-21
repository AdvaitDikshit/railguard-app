"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { InputMode } from "./ModeRail";
import type { Detection } from "@/lib/types";
import { OverlayImage } from "./OverlayImage";

export function InspectionCanvas({
  mode,
  previewUrl,
  onFileSelected,
  onRetake,
  detections,
  severity,
  disabled,
}: {
  mode: InputMode;
  previewUrl: string | null;
  onFileSelected: (file: File) => void;
  onRetake?: () => void;
  detections: Detection[] | null;
  severity: string | null;
  disabled?: boolean;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streamActive, setStreamActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // ── camera lifecycle ──────────────────────────────────────────
  useEffect(() => {
    let stream: MediaStream | null = null;
    if (mode === "camera" && !previewUrl) {
      navigator.mediaDevices
        ?.getUserMedia({ video: { facingMode: "environment" } })
        .then((s) => {
          stream = s;
          if (videoRef.current) {
            videoRef.current.srcObject = s;
            setStreamActive(true);
            setCameraError(null);
          }
        })
        .catch((e) => setCameraError(e.message || "Camera unavailable"));
    }
    return () => {
      stream?.getTracks().forEach((t) => t.stop());
      setStreamActive(false);
    };
  }, [mode, previewUrl]);

  const capture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
        onFileSelected(file);
      },
      "image/jpeg",
      0.9
    );
  }, [onFileSelected]);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      onFileSelected(files[0]);
    },
    [onFileSelected]
  );

  // ── preview + overlay (shared by upload result and camera capture) ──
  if (previewUrl) {
    const canRetake = mode === "camera" && !severity && !disabled;
    return (
      <div className="relative flex w-full items-center justify-center bg-canvas p-3">
        {disabled && (
          <div className="absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden bg-canvas-border">
            <div className="h-full w-1/3 animate-[scan_1.4s_ease-in-out_infinite] bg-accent" />
          </div>
        )}
        <OverlayImage src={previewUrl} detections={detections} severity={severity} />
        {canRetake && (
          <button
            onClick={onRetake}
            className="absolute right-4 top-4 rounded border border-canvas-border bg-canvas/90 px-3 py-1.5 text-[11px] font-medium tracking-wide text-page hover:border-accent hover:text-accent"
          >
            RETAKE
          </button>
        )}
      </div>
    );
  }

  if (mode === "camera") {
    return (
      <div className="flex h-64 w-full flex-col items-center justify-center gap-3 bg-canvas p-3">
        {cameraError ? (
          <p className="max-w-sm text-center font-mono text-[12px] text-page/70">
            Camera unavailable: {cameraError}. Use Upload instead, or check browser permissions.
          </p>
        ) : (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="max-h-48 max-w-full rounded-sm border border-canvas-border"
            />
            <button
              onClick={capture}
              disabled={!streamActive || disabled}
              className="rounded bg-accent px-5 py-2 text-[13px] font-medium tracking-wide text-white disabled:opacity-40"
            >
              CAPTURE FRAME
            </button>
          </>
        )}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    );
  }

  // ── upload drop zone (default) ──────────────────────────────────
  return (
    <div
      className={[
        "flex h-64 w-full cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed p-8 text-center transition-colors",
        dragOver ? "border-accent bg-accent-soft" : "border-canvas-border bg-canvas",
      ].join(" ")}
      onClick={() => fileInputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <p className={`font-mono text-[13px] ${dragOver ? "text-ink" : "text-page/80"}`}>
        Drop a track photograph here, or click to browse
      </p>
      <p className={`font-mono text-[11px] ${dragOver ? "text-ink/60" : "text-page/40"}`}>
        JPG · PNG · BMP · TIFF · WEBP — up to 15MB
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.bmp,.tif,.tiff,.webp"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
