import type { Message } from "@langchain/langgraph-sdk";
import { useParams } from "next/navigation";
import { memo, useMemo } from "react";

import {
  Message as AIElementMessage,
  MessageContent as AIElementMessageContent,
  MessageResponse as AIElementMessageResponse,
  MessageToolbar,
  MessageAttachment,
  MessageAttachments,
} from "@/components/ai-elements/message";
import { resolveArtifactURL } from "@/core/artifacts/utils";
import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import { cn } from "@/lib/utils";

import { CopyButton } from "../copy-button";

// Type definition for structured message content blocks
type MessageContentBlock =
  | { type: "text"; text: string }
  | { type: "image_url"; image_url: string | { url: string } };

export function MessageListItem({
  className,
  message,
  isLoading,
}: {
  className?: string;
  message: Message;
  isLoading?: boolean;
}) {
  return (
    <AIElementMessage
      className={cn("group/conversation-message relative w-full", className)}
      from={message.type === "human" ? "user" : "assistant"}
    >
      <MessageContent
        className={message.type === "human" ? "w-fit" : "w-full"}
        message={message}
        isLoading={isLoading}
      />
      <MessageToolbar
        className={cn(
          message.type === "human" && "justify-end",
          message.type === "human" ? "-bottom-9" : "-bottom-8",
          "absolute right-0 left-0 z-20 opacity-0 transition-opacity delay-200 duration-300 group-hover/conversation-message:opacity-100",
        )}
      >
        <div className="flex gap-1">
          <CopyButton
            clipboardData={
              extractContentFromMessage(message)
                ? extractContentFromMessage(message)
                : (extractReasoningContentFromMessage(message) ?? "")
            }
          />
        </div>
      </MessageToolbar>
    </AIElementMessage>
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
  const content = useMemo(() => {
    const reasoningContent = extractReasoningContentFromMessage(message);
    const content = extractContentFromMessage(message);
    if (!isLoading && reasoningContent && !content) {
      return reasoningContent;
    }
    return content;
  }, [isLoading, message]);
  const { thread_id } = useParams<{ thread_id: string }>();

  // Check if content is an array with image_url elements
  const messageContent = message.content;
  const isImageArrayContent = Array.isArray(messageContent) &&
    messageContent.length > 0 &&
    messageContent.some((item: MessageContentBlock) => item.type === "image_url");

  return (
    <AIElementMessageContent className={className}>
      {isImageArrayContent ? (
        <MessageAttachments>
          {messageContent.map((item: MessageContentBlock, index: number) => {
            if (item.type === "image_url") {
              const url = typeof item.image_url === "string"
                ? item.image_url
                : item.image_url?.url;
              const resolvedUrl = url && url.startsWith("/mnt/")
                ? resolveArtifactURL(url, thread_id)
                : url;

              return (
                <MessageAttachment
                  key={index}
                  data={{
                    type: "file",
                    url: resolvedUrl,
                    filename: `image-${index + 1}`,
                    mediaType: "image/*",
                  }}
                />
              );
            }
            return null;
          })}
        </MessageAttachments>
      ) : (
        <AIElementMessageResponse
          rehypePlugins={rehypePlugins}
          components={{
            img: ({ src, alt }: React.ImgHTMLAttributes<HTMLImageElement>) => {
              if (!src) return null;
              if (typeof src !== "string") {
                return (
                  <img
                    className="max-w-full overflow-hidden rounded-lg"
                    src={src}
                    alt={alt}
                  />
                );
              }
              let url = src;
              if (src.startsWith("/mnt/")) {
                url = resolveArtifactURL(src, thread_id);
              }
              return (
                <a href={url} target="_blank" rel="noopener noreferrer">
                  <img
                    className="max-w-full overflow-hidden rounded-lg"
                    src={url}
                    alt={alt}
                  />
                </a>
              );
            },
          }}
        >
          {content}
        </AIElementMessageResponse>
      )}
    </AIElementMessageContent>
  );
}
const MessageContent = memo(MessageContent_);
