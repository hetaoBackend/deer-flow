"use client";

import { MoreHorizontal, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useCallback } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { useDeleteThread, useThreads } from "@/core/threads/hooks";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { env } from "@/env";

export function RecentChatList() {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const { data: threads = [] } = useThreads();
  const { mutate: deleteThread } = useDeleteThread();
  const handleDelete = useCallback(
    (threadId: string) => {
      deleteThread({ threadId });
      if (threadId === threadIdFromPath) {
        const threadIndex = threads.findIndex((t) => t.thread_id === threadId);
        let nextThreadId = "new";
        if (threadIndex > -1) {
          if (threads[threadIndex + 1]) {
            nextThreadId = threads[threadIndex + 1]!.thread_id;
          } else if (threads[threadIndex - 1]) {
            nextThreadId = threads[threadIndex - 1]!.thread_id;
          }
        }
        void router.push(`/workspace/chats/${nextThreadId}`);
      }
    },
    [deleteThread, router, threadIdFromPath, threads],
  );
  if (threads.length === 0) {
    return null;
  }
  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true"
          ? t.sidebar.recentChats
          : t.sidebar.demoChats}
      </SidebarGroupLabel>
      <SidebarGroupContent className="group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0">
        <SidebarMenu>
          <div className="flex w-full flex-col gap-1">
            {threads.map((thread) => {
              const isActive = pathOfThread(thread.thread_id) === pathname;
              return (
                <SidebarMenuItem
                  key={thread.thread_id}
                  className="group/side-menu-item"
                >
                  <SidebarMenuButton isActive={isActive} asChild>
                    <div>
                      <Link
                        className="text-muted-foreground block w-full whitespace-nowrap group-hover/side-menu-item:overflow-hidden"
                        href={pathOfThread(thread.thread_id)}
                      >
                        {titleOfThread(thread)}
                      </Link>
                      {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true" && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <SidebarMenuAction
                              showOnHover
                              className="bg-background/50 hover:bg-background"
                            >
                              <MoreHorizontal />
                              <span className="sr-only">{t.common.more}</span>
                            </SidebarMenuAction>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent
                            className="w-48 rounded-lg"
                            side={"right"}
                            align={"start"}
                          >
                            <DropdownMenuItem
                              onSelect={() => handleDelete(thread.thread_id)}
                            >
                              <Trash2 className="text-muted-foreground" />
                              <span>{t.common.delete}</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </div>
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
