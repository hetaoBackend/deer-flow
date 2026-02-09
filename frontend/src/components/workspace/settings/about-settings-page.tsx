"use client";

import { Streamdown } from "streamdown";

import about from "./about.md";

export function AboutSettingsPage() {
  return <Streamdown>{about}</Streamdown>;
}
