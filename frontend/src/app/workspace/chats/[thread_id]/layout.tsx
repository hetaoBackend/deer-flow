"use client";

import { ArtifactsProvider } from "@/components/workspace/artifacts";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ArtifactsProvider>{children}</ArtifactsProvider>;
}
