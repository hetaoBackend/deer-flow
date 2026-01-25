import type { UseStream } from "@langchain/langgraph-sdk/react";

import {
  Conversation,
  ConversationContent,
} from "@/components/ai-elements/conversation";
import { MessageResponse } from "@/components/ai-elements/message";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import type { AgentThreadState } from "@/core/threads";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { StreamingIndicator } from "../streaming-indicator";

import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import { MessageListSkeleton } from "./skeleton";

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = 160,
}: {
  className?: string;
  threadId: string;
  thread: UseStream<AgentThreadState>;
  paddingBottom?: number;
}) {
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  if (thread.isThreadLoading) {
    return <MessageListSkeleton />;
  }
  return (
    <Conversation
      className={cn("flex size-full flex-col justify-center", className)}
    >
      <ConversationContent className="mx-auto w-full max-w-(--container-width-md) gap-10 pt-12">
        {groupMessages(thread.messages, (group) => {
          if (group.type === "human" || group.type === "assistant") {
            return (
              <MessageListItem
                key={group.id}
                message={group.messages[0]!}
                isLoading={thread.isLoading}
              />
            );
          }
          if (group.type === "assistant:present-files") {
            const files: string[] = [];
            for (const message of group.messages) {
              if (hasPresentFiles(message)) {
                const presentFiles = extractPresentFilesFromMessage(message);
                files.push(...presentFiles);
              }
            }
            return (
              <div className="w-full" key={group.id}>
                {group.messages[0] && hasContent(group.messages[0]) && (
                  <MessageResponse
                    className="mb-4"
                    rehypePlugins={rehypePlugins}
                  >
                    {extractContentFromMessage(group.messages[0])}
                  </MessageResponse>
                )}
                <ArtifactFileList files={files} threadId={threadId} />
              </div>
            );
          }
          return (
            <MessageGroup
              key={"group-" + group.id}
              messages={group.messages}
              isLoading={thread.isLoading}
            />
          );
        })}
        {thread.isLoading && <StreamingIndicator className="my-4" />}
        <div style={{ height: `${paddingBottom}px` }} />
      </ConversationContent>
    </Conversation>
  );
}
