import type { HumanMessage } from "@langchain/core/messages";
import type { ThreadsClient } from "@langchain/langgraph-sdk/client";
import { useStream, type UseStream } from "@langchain/langgraph-sdk/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";

import { getAPIClient } from "../api";
import { uploadFiles } from "../uploads";
import type { UploadedFileInfo } from "../uploads";

import type {
  AgentThread,
  AgentThreadContext,
  AgentThreadState,
} from "./types";

export function useThreadStream({
  threadId,
  isNewThread,
}: {
  isNewThread: boolean;
  threadId: string | null | undefined;
}) {
  const queryClient = useQueryClient();
  const thread = useStream<AgentThreadState>({
    client: getAPIClient(),
    assistantId: "lead_agent",
    threadId: isNewThread ? undefined : threadId,
    reconnectOnMount: true,
    fetchStateHistory: true,
    onFinish(state) {
      // void queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread>) => {
          return oldData.map((t) => {
            if (t.thread_id === threadId) {
              return {
                ...t,
                values: {
                  ...t.values,
                  title: state.values.title,
                },
              };
            }
            return t;
          });
        },
      );
    },
  });
  return thread;
}

export function useSubmitThread({
  threadId,
  thread,
  threadContext,
  isNewThread,
  afterSubmit,
}: {
  isNewThread: boolean;
  threadId: string | null | undefined;
  thread: UseStream<AgentThreadState>;
  threadContext: Omit<AgentThreadContext, "thread_id">;
  afterSubmit?: () => void;
}) {
  const queryClient = useQueryClient();
  const callback = useCallback(
    async (message: PromptInputMessage) => {
    let uploadedFilesInfo: UploadedFileInfo[] = [];
      const text = message.text.trim();

      // Upload files first if any
      if (message.files && message.files.length > 0) {
        try {
          // Convert FileUIPart to File objects by fetching blob URLs
          const filePromises = message.files.map(async (fileUIPart) => {
            if (fileUIPart.url && fileUIPart.filename) {
              try {
                // Fetch the blob URL to get the file data
                const response = await fetch(fileUIPart.url);
                const blob = await response.blob();

                // Create a File object from the blob
                return new File([blob], fileUIPart.filename, {
                  type: fileUIPart.mediaType || blob.type,
                });
              } catch (error) {
                console.error(
                  `Failed to fetch file ${fileUIPart.filename}:`,
                  error,
                );
                return null;
              }
            }
            return null;
          });

          const files = (await Promise.all(filePromises)).filter(
            (file): file is File => file !== null,
          );

          if (files.length > 0) {
            if (!threadId) {
              throw new Error("Thread ID is required for file upload");
            }
            const uploadResult = await uploadFiles(threadId, files);
            uploadedFilesInfo = uploadResult.files;
          }
        } catch (error) {
          console.error("Failed to upload files:", error);
          // Continue with message submission even if upload fails
          // You might want to show an error toast here
        }
      }

      // Build message text with image markdown if images were uploaded
      let messageText = text;
      const fileMap = new Map(
        uploadedFilesInfo.map(f => [f.filename, f])
      );

      // Append image markdown for any uploaded images
      if (message.files && message.files.length > 0) {
        const imageMarkdownParts: string[] = [];
        for (const originalFile of message.files) {
          const filename = originalFile.filename;
          if (!filename) continue;
          const uploadedInfo = fileMap.get(filename);
          if (uploadedInfo) {
            const isImage = originalFile.mediaType?.startsWith("image/");
            if (isImage) {
              // For images, add markdown format so frontend can display them
              // Use virtual_path which starts with /mnt/ and will be resolved to artifact URL
              imageMarkdownParts.push(`![${uploadedInfo.filename}](${uploadedInfo.virtual_path})`);
            }
          }
        }
        if (imageMarkdownParts.length > 0) {
          messageText = text ? (text + "\n\n" + imageMarkdownParts.join("\n")) : imageMarkdownParts.join("\n");
        }
      }

      await thread.submit(
        {
          messages: [
            {
              type: "human",
              content: messageText,
            },
          ] as HumanMessage[],
        },
        {
          threadId: isNewThread ? threadId! : undefined,
          streamSubgraphs: true,
          streamResumable: true,
          config: {
            recursion_limit: 1000,
          },
          context: {
            ...threadContext,
            thread_id: threadId,
          },
        },
      );
      void queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
      afterSubmit?.();
    },
    [thread, isNewThread, threadId, threadContext, queryClient, afterSubmit],
  );
  return callback;
}

export function useThreads(
  params: Parameters<ThreadsClient["search"]>[0] = {
    limit: 50,
    sortBy: "updated_at",
    sortOrder: "desc",
  },
) {
  const apiClient = getAPIClient();
  return useQuery<AgentThread[]>({
    queryKey: ["threads", "search", params],
    queryFn: async () => {
      const response = await apiClient.threads.search<AgentThreadState>(params);
      return response as AgentThread[];
    },
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  const apiClient = getAPIClient();
  return useMutation({
    mutationFn: async ({ threadId }: { threadId: string }) => {
      await apiClient.threads.delete(threadId);
    },
    onSuccess(_, { threadId }) {
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread>) => {
          return oldData.filter((t) => t.thread_id !== threadId);
        },
      );
    },
  });
}
