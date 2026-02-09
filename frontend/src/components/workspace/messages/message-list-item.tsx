import type { Message } from "@langchain/langgraph-sdk";
import { FileIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { memo, useMemo } from "react";
import rehypeKatex from "rehype-katex";

import {
  CitationLink,
  CitationsLoadingIndicator,
} from "@/components/ai-elements/inline-citation";
import {
  Message as AIElementMessage,
  MessageContent as AIElementMessageContent,
  MessageResponse as AIElementMessageResponse,
  MessageToolbar,
} from "@/components/ai-elements/message";
import { Badge } from "@/components/ui/badge";
import { resolveArtifactURL } from "@/core/artifacts/utils";
import {
  type Citation,
  buildCitationMap,
  isCitationsBlockIncomplete,
  parseCitations,
  removeAllCitations,
} from "@/core/citations";
import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  parseUploadedFiles,
  type UploadedFile,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import { humanMessagePlugins, streamdownPlugins } from "@/core/streamdown";
import { cn } from "@/lib/utils";

import { CopyButton } from "../copy-button";

export function MessageListItem({
  className,
  message,
  isLoading,
}: {
  className?: string;
  message: Message;
  isLoading?: boolean;
}) {
  const isHuman = message.type === "human";
  return (
    <AIElementMessage
      className={cn("group/conversation-message relative w-full", className)}
      from={isHuman ? "user" : "assistant"}
    >
      <MessageContent
        className={isHuman ? "w-fit" : "w-full"}
        message={message}
        isLoading={isLoading}
      />
      <MessageToolbar
        className={cn(
          isHuman ? "justify-end -bottom-9" : "-bottom-8",
          "absolute right-0 left-0 z-20 opacity-0 transition-opacity delay-200 duration-300 group-hover/conversation-message:opacity-100",
        )}
      >
        <div className="flex gap-1">
          <CopyButton
            clipboardData={removeAllCitations(
              extractContentFromMessage(message) ??
              extractReasoningContentFromMessage(message) ??
              ""
            )}
          />
        </div>
      </MessageToolbar>
    </AIElementMessage>
  );
}

/**
 * Custom link component that handles citations and external links
 * Only links in citationMap are rendered as CitationLink badges
 * Other links (project URLs, regular links) are rendered as plain links
 */
function MessageLink({
  href,
  children,
  citationMap,
  isHuman,
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  citationMap: Map<string, Citation>;
  isHuman: boolean;
}) {
  if (!href) return <span>{children}</span>;

  const citation = citationMap.get(href);
  
  // Only render as CitationLink badge if it's a citation (in citationMap) and not human message
  if (citation && !isHuman) {
    return (
      <CitationLink citation={citation} href={href}>
        {children}
      </CitationLink>
    );
  }

  // All other links render as plain links
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline underline-offset-2 hover:no-underline"
    >
      {children}
    </a>
  );
}

/**
 * Custom image component that handles artifact URLs
 */
function MessageImage({
  src,
  alt,
  threadId,
  maxWidth = "90%",
  ...props
}: React.ImgHTMLAttributes<HTMLImageElement> & {
  threadId: string;
  maxWidth?: string;
}) {
  if (!src) return null;

  const imgClassName = cn("overflow-hidden rounded-lg", `max-w-[${maxWidth}]`);
  
  if (typeof src !== "string") {
    return <img className={imgClassName} src={src} alt={alt} {...props} />;
  }
  
  const url = src.startsWith("/mnt/") ? resolveArtifactURL(src, threadId) : src;
  
  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      <img className={imgClassName} src={url} alt={alt} {...props} />
    </a>
  );
}

function MessageContent_({
  className,
  message,
  isLoading = false,
}: {
  className?: string;
  message: Message;
  isLoading?: boolean;
}) {
  const rehypePlugins = useRehypeSplitWordsIntoSpans(isLoading);
  const isHuman = message.type === "human";
  const { thread_id } = useParams<{ thread_id: string }>();

  // Extract and parse citations and uploaded files from message content
  const { citations, cleanContent, uploadedFiles, isLoadingCitations } =
    useMemo(() => {
      const reasoningContent = extractReasoningContentFromMessage(message);
      const rawContent = extractContentFromMessage(message);

      // When only reasoning content exists (no main content), also parse citations
      if (!isLoading && reasoningContent && !rawContent) {
        const { citations, cleanContent } = parseCitations(reasoningContent);
        return {
          citations,
          cleanContent,
          uploadedFiles: [],
          isLoadingCitations: false,
        };
      }

      // For human messages, parse uploaded files first
      if (isHuman && rawContent) {
        const { files, cleanContent: contentWithoutFiles } =
          parseUploadedFiles(rawContent);
        const { citations, cleanContent: finalContent } =
          parseCitations(contentWithoutFiles);
        return {
          citations,
          cleanContent: finalContent,
          uploadedFiles: files,
          isLoadingCitations: false,
        };
      }

      const { citations, cleanContent } = parseCitations(rawContent ?? "");
      const isLoadingCitations =
        isLoading && isCitationsBlockIncomplete(rawContent ?? "");

      return { citations, cleanContent, uploadedFiles: [], isLoadingCitations };
    }, [isLoading, message, isHuman]);

  const citationMap = useMemo(() => buildCitationMap(citations), [citations]);

  // Shared markdown components
  const markdownComponents = useMemo(() => ({
    a: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
      <MessageLink {...props} citationMap={citationMap} isHuman={isHuman} />
    ),
    img: (props: React.ImgHTMLAttributes<HTMLImageElement>) => (
      <MessageImage {...props} threadId={thread_id} maxWidth={isHuman ? "full" : "90%"} />
    ),
  }), [citationMap, thread_id, isHuman]);

  // Render message response
  // Human messages use humanMessagePlugins (no autolink) to prevent URL bleeding into adjacent text
  const messageResponse = cleanContent ? (
    <AIElementMessageResponse
      remarkPlugins={isHuman ? humanMessagePlugins.remarkPlugins : streamdownPlugins.remarkPlugins}
      rehypePlugins={isHuman ? humanMessagePlugins.rehypePlugins : [...rehypePlugins, [rehypeKatex, { output: "html" }]]}
      components={markdownComponents}
    >
      {cleanContent}
    </AIElementMessageResponse>
  ) : null;

  // Uploaded files list
  const filesList = uploadedFiles.length > 0 && thread_id ? (
    <UploadedFilesList files={uploadedFiles} threadId={thread_id} />
  ) : null;

  // Citations loading indicator
  const citationsLoadingIndicator = isLoadingCitations ? (
    <CitationsLoadingIndicator citations={citations} className="my-3" />
  ) : null;

  // Human messages with uploaded files: render outside bubble
  if (isHuman && uploadedFiles.length > 0) {
    return (
      <div className={cn("ml-auto flex flex-col gap-2", className)}>
        {filesList}
        {messageResponse && (
          <AIElementMessageContent className="w-fit">
            {messageResponse}
          </AIElementMessageContent>
        )}
      </div>
    );
  }

  // Default rendering
  return (
    <AIElementMessageContent className={className}>
      {filesList}
      {messageResponse}
      {citationsLoadingIndicator}
    </AIElementMessageContent>
  );
}

/**
 * Get file extension and check helpers
 */
const getFileExt = (filename: string) => filename.split(".").pop()?.toLowerCase() ?? "";

const FILE_TYPE_MAP: Record<string, string> = {
  json: "JSON", csv: "CSV", txt: "TXT", md: "Markdown",
  py: "Python", js: "JavaScript", ts: "TypeScript", tsx: "TSX", jsx: "JSX",
  html: "HTML", css: "CSS", xml: "XML", yaml: "YAML", yml: "YAML",
  pdf: "PDF", png: "PNG", jpg: "JPG", jpeg: "JPEG", gif: "GIF",
  svg: "SVG", zip: "ZIP", tar: "TAR", gz: "GZ",
};

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"];

function getFileTypeLabel(filename: string): string {
  const ext = getFileExt(filename);
  return FILE_TYPE_MAP[ext] ?? (ext.toUpperCase() || "FILE");
}

function isImageFile(filename: string): boolean {
  return IMAGE_EXTENSIONS.includes(getFileExt(filename));
}

/**
 * Uploaded files list component
 */
function UploadedFilesList({ files, threadId }: { files: UploadedFile[]; threadId: string }) {
  if (files.length === 0) return null;

  return (
    <div className="mb-2 flex flex-wrap justify-end gap-2">
      {files.map((file, index) => (
        <UploadedFileCard key={`${file.path}-${index}`} file={file} threadId={threadId} />
      ))}
    </div>
  );
}

/**
 * Single uploaded file card component
 */
function UploadedFileCard({ file, threadId }: { file: UploadedFile; threadId: string }) {
  if (!threadId) return null;

  const isImage = isImageFile(file.filename);
  const fileUrl = resolveArtifactURL(file.path, threadId);

  if (isImage) {
    return (
      <a
        href={fileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="group border-border/40 relative block overflow-hidden rounded-lg border"
      >
        <img
          src={fileUrl}
          alt={file.filename}
          className="h-32 w-auto max-w-[240px] object-cover transition-transform group-hover:scale-105"
        />
      </a>
    );
  }

  return (
    <div className="bg-background border-border/40 flex max-w-[200px] min-w-[120px] flex-col gap-1 rounded-lg border p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <FileIcon className="text-muted-foreground mt-0.5 size-4 shrink-0" />
        <span className="text-foreground truncate text-sm font-medium" title={file.filename}>
          {file.filename}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <Badge variant="secondary" className="rounded px-1.5 py-0.5 text-[10px] font-normal">
          {getFileTypeLabel(file.filename)}
        </Badge>
        <span className="text-muted-foreground text-[10px]">{file.size}</span>
      </div>
    </div>
  );
}

const MessageContent = memo(MessageContent_);
