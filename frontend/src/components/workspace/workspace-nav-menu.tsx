"use client";

import {
  BugIcon,
  ChevronsUpDown,
  GlobeIcon,
  InfoIcon,
  MailIcon,
  Settings2Icon,
  SettingsIcon,
} from "lucide-react";
import { useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";

import { GithubIcon } from "./github-icon";
import { SettingsDialog } from "./settings";

export function WorkspaceNavMenu() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { open: isSidebarOpen } = useSidebar();
  const { t } = useI18n();
  return (
    <>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <SidebarMenu className="w-full">
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <SidebarMenuButton
                size="lg"
                className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                {isSidebarOpen ? (
                  <div className="text-muted-foreground flex w-full items-center gap-2 text-left text-sm">
                    <SettingsIcon className="size-4" />
                    <span>{t.workspace.settingsAndMore}</span>
                    <ChevronsUpDown className="text-muted-foreground ml-auto size-4" />
                  </div>
                ) : (
                  <div className="flex size-full items-center justify-center">
                    <SettingsIcon className="text-muted-foreground size-4" />
                  </div>
                )}
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
              align="end"
              sideOffset={4}
            >
              <DropdownMenuGroup>
                <DropdownMenuItem onClick={() => setSettingsOpen(true)}>
                  <Settings2Icon />
                  {t.common.settings}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <a
                  href="https://deerflow.tech/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <DropdownMenuItem>
                    <GlobeIcon />
                    {t.workspace.officialWebsite}
                  </DropdownMenuItem>
                </a>
                <a
                  href="https://github.com/bytedance/deer-flow"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <DropdownMenuItem>
                    <GithubIcon />
                    {t.workspace.visitGithub}
                  </DropdownMenuItem>
                </a>
                <DropdownMenuSeparator />
                <a
                  href="https://github.com/bytedance/deer-flow/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <DropdownMenuItem>
                    <BugIcon />
                    {t.workspace.reportIssue}
                  </DropdownMenuItem>
                </a>
                <a href="mailto:lixin.henry@bytedance.com">
                  <DropdownMenuItem>
                    <MailIcon />
                    {t.workspace.contactUs}
                  </DropdownMenuItem>
                </a>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <InfoIcon />
                {t.workspace.about}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
    </>
  );
}
