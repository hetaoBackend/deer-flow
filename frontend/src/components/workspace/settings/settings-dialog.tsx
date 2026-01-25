"use client";

import { PaletteIcon, SparklesIcon, WrenchIcon } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AcknowledgePage } from "@/components/workspace/settings/acknowledge-page";
import { AppearanceSettingsPage } from "@/components/workspace/settings/appearance-settings-page";
import { SkillSettingsPage } from "@/components/workspace/settings/skill-settings-page";
import { ToolSettingsPage } from "@/components/workspace/settings/tool-settings-page";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

type SettingsSection = "appearance" | "tools" | "skills" | "acknowledge";

type SettingsDialogProps = React.ComponentProps<typeof Dialog> & {
  defaultSection?: SettingsSection;
};

export function SettingsDialog({
  defaultSection = "appearance",
  ...dialogProps
}: SettingsDialogProps) {
  const { t } = useI18n();
  const [activeSection, setActiveSection] =
    useState<SettingsSection>(defaultSection);

  const sections = useMemo(
    () => [
      {
        id: "appearance",
        label: t.settings.sections.appearance,
        icon: PaletteIcon,
      },
      { id: "tools", label: t.settings.sections.tools, icon: WrenchIcon },
      { id: "skills", label: t.settings.sections.skills, icon: SparklesIcon },
    ],
    [
      t.settings.sections.appearance,
      t.settings.sections.tools,
      t.settings.sections.skills,
    ],
  );
  return (
    <Dialog {...dialogProps}>
      <DialogContent
        className="flex h-[75vh] max-h-[calc(100vh-2rem)] flex-col sm:max-w-5xl md:max-w-6xl"
        aria-describedby={undefined}
      >
        <DialogHeader className="gap-1">
          <DialogTitle>{t.settings.title}</DialogTitle>
          <p className="text-muted-foreground text-sm">
            {t.settings.description}
          </p>
        </DialogHeader>
        <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[220px_1fr]">
          <nav className="bg-sidebar min-h-0 overflow-y-auto rounded-lg border p-2">
            <ul className="space-y-1 pr-1">
              {sections.map(({ id, label, icon: Icon }) => {
                const active = activeSection === id;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => setActiveSection(id as SettingsSection)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="size-4" />
                      <span>{label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          <ScrollArea className="h-full min-h-0 rounded-lg border">
            <div className="space-y-8 p-6">
              {activeSection === "appearance" && <AppearanceSettingsPage />}
              {activeSection === "tools" && <ToolSettingsPage />}
              {activeSection === "skills" && <SkillSettingsPage />}
              {activeSection === "acknowledge" && <AcknowledgePage />}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
