// Mirrors api/app/schemas.py — keep in sync with the backend.

export interface Detection {
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // x1, y1, x2, y2 in original image pixels
  width_px: number;
  height_px: number;
  area_frac: number;
  size_cat: "hairline" | "small" | "medium" | "large" | string;
}

export interface Location {
  lat: number | null;
  lng: number | null;
  accuracy_m: number | null;
  source: string | null;
  nearest_station: string | null;
}

export interface Severity {
  ai_severity: "NO_CRACK" | "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | string;
  ai_max_confidence: number;
  ai_detection_count: number;
  ai_heading: string | null;
  ai_risk_summary: string | null;
  ai_actions: string[] | null;
  ai_timeline: string | null;
  ai_authority: string | null;

  engineering_severity: string | null;
  engineering_notes: string | null;
  verified_by: string | null;
  verified_at: string | null;
}

export interface Report {
  id: string;
  status: string;
  source: string;
  created_at: string;
  original_url: string | null;
  annotated_url: string | null;
  location: Location | null;
  severity: Severity | null;
  detections: Detection[];
  cluster_id: string | null;
}

export interface ReportSummary {
  id: string;
  status: string;
  created_at: string;
  ai_severity: string | null;
  detection_count: number | null;
  annotated_url: string | null;
  lat: number | null;
  lng: number | null;
}

export interface VideoDetection {
  track_id: number;
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number];
  size_cat: string;
  first_seen_s: number;
  frame_count: number;
}

export interface VideoReport {
  id: string;
  status: string;
  created_at: string;
  video_url: string | null;
  duration_s: number | null;
  fps: number | null;
  frames_analyzed: number | null;
  location: Location | null;
  severity: Severity | null;
  detections: VideoDetection[];
}
